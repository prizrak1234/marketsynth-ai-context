"""Business Idea Validation skill — search/fetch → source → evidence → verdict."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.business_idea_validation.classification import classify_evidence_item
from app.business_idea_validation.commercial_relevance import assess_commercial_relevance
from app.business_idea_validation.confidence import calculate_confidence
from app.business_idea_validation.coverage_gate import evaluate_coverage_gate, positive_verdict_allowed
from app.business_idea_validation.extraction import detect_contradiction_pairs, extract_claims
from app.business_idea_validation.findings import (
    build_findings,
    build_hypothesis_findings,
    build_opportunities,
    build_research_gaps,
    build_risks,
    confirmed_evidence,
)
from app.business_idea_validation.evidence_validation import validate_evidence_acceptance
from app.business_idea_validation.relevance import assess_source_relevance
from app.business_idea_validation.sanitization import (
    domain_from_url,
    sanitize_evidence_statement,
    sanitize_source_body,
)
from app.business_idea_validation.audience_segmentation import run_audience_segmentation
from app.business_idea_validation.coverage_plan import (
    build_initial_coverage_plan,
    mark_categories_searching,
    update_coverage_plan,
)
from app.business_idea_validation.customer_report import build_customer_research_report
from app.business_idea_validation.internal_report import build_internal_research_diagnostics
from app.business_idea_validation.commercial_verdict import (
    build_commercial_verdict,
    map_legacy_verdict_kind,
)
from app.business_idea_validation.evidence_contract import (
    build_evidence_items,
    build_finding_items,
)
from app.business_idea_validation.run_progress import BivRunProgressTracker
from app.business_idea_validation.run_observability import BivRunObservabilityRecorder
from app.business_idea_validation.fetch_orchestrator import BivFetchOrchestrator
from app.business_idea_validation.pipeline_validator import PipelineValidationResult, validate_pipeline
from app.business_idea_validation.pipeline_metrics import BivPipelineMetricsRecorder
from app.business_idea_validation.content_extraction import (
    ExtractionRunContext,
    ExtractionStatus,
    extract_and_normalize_document,
)
from app.business_idea_validation.evidence_floors import (
    apply_floor_verdict_constraints,
    count_floors_met,
    evaluate_category_floors,
)
from app.business_idea_validation.report_validator import validate_customer_report
from app.business_idea_validation.research_cascade import build_cascade_research_plan, phases_completed
from app.business_idea_validation.coverage_contract import (
    attach_semantic_groups_to_gaps,
    build_category_coverage,
    build_partial_report,
    build_remediation_questions,
    build_research_stop_reason,
    build_semantic_gap_groups,
    dedupe_research_gaps,
    CoverageAttemptTracker,
    normalize_category,
)
from app.business_idea_validation.gap_presentation import present_research_gaps
from app.business_idea_validation.partial_research_delivery import (
    PartialResearchBuildContext,
    build_partial_research_output,
    can_deliver_partial_research,
)
from app.business_idea_validation.source_quality import classify_source
from app.business_idea_validation.verdict_mapper import (
    default_next_steps,
    map_to_business_verdict_kind,
    map_to_confidence_level,
    resolve_verdict_kind,
)
from app.core.config import Settings
from app.core.exceptions import InvalidStateError, ResearchPipelineError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.source import SourceTable
from app.domain.source_fingerprint import compute_source_fingerprint, normalize_url
from app.mcp.client import McpClient
from app.schemas.contracts import (
    BivEvidenceClassification,
    BivPipelineFailure,
    BivPipelineStage,
    BivResearchTerminalState,
    BivSourceReference,
    BivStructuredEvidenceType,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationSourceSummary,
    BusinessIdeaValidationVerdictKind,
    BusinessVerdictCreate,
    BusinessVerdictEvidenceLinkCreate,
    BusinessVerdictEvidenceRole,
    BusinessVerdictPreparedByType,
    EvidenceAssessmentState,
    EvidenceConfidenceLevel,
    EvidenceCreateRequest,
    EvidenceInvestigationArea,
    EvidenceMateriality,
    EvidenceReviewNoteRequest,
    EvidenceSourceLinkInput,
    EvidenceSourceStance,
    EvidenceType,
    InvestigationStageId,
    InvestigationStageStatus,
    InvestigationStageUpdateRequest,
    SourceCapability,
    SourceCreateRequest,
    SourceProvenanceType,
    SourceStatus,
    SourceType,
    VerdictCondition,
    VerdictConditionStatus,
    VerdictCriticalRisk,
    VerdictFinding,
    VerdictRiskProbability,
    VerdictRiskSeverity,
    VerdictSensitivity,
)
from app.services.business_verdict_service import BusinessVerdictService
from app.services.evidence_service import EvidenceService
from app.services.investigation_service import InvestigationService
from app.services.source_service import SourceService
from app.services.transaction import transactional


_AREA_MAP = {
    "market": EvidenceInvestigationArea.MARKET_RESEARCH,
    "demand": EvidenceInvestigationArea.MARKET_RESEARCH,
    "competitors": EvidenceInvestigationArea.COMPETITOR_ANALYSIS,
    "audience": EvidenceInvestigationArea.AUDIENCE_ANALYSIS,
    "pricing": EvidenceInvestigationArea.MARKET_RESEARCH,
    "commercial_risks": EvidenceInvestigationArea.RISK_ASSESSMENT,
    "local_context": EvidenceInvestigationArea.MARKET_RESEARCH,
    "market_demand": EvidenceInvestigationArea.MARKET_RESEARCH,
    "competition": EvidenceInvestigationArea.COMPETITOR_ANALYSIS,
    "target_audience": EvidenceInvestigationArea.AUDIENCE_ANALYSIS,
}

_STAGE_MAP = {
    "market": InvestigationStageId.MARKET_RESEARCH,
    "demand": InvestigationStageId.MARKET_RESEARCH,
    "competitors": InvestigationStageId.COMPETITOR_ANALYSIS,
    "audience": InvestigationStageId.AUDIENCE_ANALYSIS,
    "pricing": InvestigationStageId.MARKET_RESEARCH,
    "commercial_risks": InvestigationStageId.RISK_ASSESSMENT,
    "local_context": InvestigationStageId.MARKET_RESEARCH,
    "market_demand": InvestigationStageId.MARKET_RESEARCH,
    "competition": InvestigationStageId.COMPETITOR_ANALYSIS,
    "target_audience": InvestigationStageId.AUDIENCE_ANALYSIS,
}

MAX_RESEARCH_ROUNDS = 6
MAX_MCP_SEARCH_CALLS = 32
MAX_MCP_FETCH_CALLS = 40


def _research_budgets(settings: Settings) -> tuple[int, int]:
    return settings.biv_research_max_search_calls, settings.biv_research_max_fetch_calls
FETCHES_PER_CATEGORY = 3


_PHASE_TO_PROGRESS: dict[str, BivPipelineStage] = {
    "direct": BivPipelineStage.SEARCHING_DIRECT,
    "indirect": BivPipelineStage.SEARCHING_INDIRECT,
    "international": BivPipelineStage.SEARCHING_INTERNATIONAL,
    "local": BivPipelineStage.SEARCHING_LOCAL,
    "adjacent": BivPipelineStage.SEARCHING_ADJACENT,
    "transferability": BivPipelineStage.SEARCHING_ADJACENT,
}


class BusinessIdeaValidationSkill:
    SKILL_CODE = "business_idea_validation"
    SKILL_VERSION = "cmvp1_1_v1"

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._mcp = McpClient(session, settings)
        self._sources = SourceService(session)
        self._evidence = EvidenceService(session)
        self._verdicts = BusinessVerdictService(session)
        self._investigations = InvestigationService(session)
        self._cached_investigation_id: UUID | None = None

    async def run(
        self,
        inp: BusinessIdeaValidationInput,
        *,
        run_id: UUID | None = None,
        progress: BivRunProgressTracker | None = None,
        observability: BivRunObservabilityRecorder | None = None,
    ) -> BusinessIdeaValidationOutput:
        if not self._settings.business_idea_validation_enabled:
            raise InvalidStateError("business_idea_validation_disabled")

        if progress:
            progress.advance(BivPipelineStage.NORMALIZING_INPUT)

        plan_items = build_cascade_research_plan(inp)
        pipeline_metrics = BivPipelineMetricsRecorder()
        pipeline_metrics.record_queries_generated(len(plan_items))
        correlation_id = observability.snapshot().correlation_id if observability else uuid4().hex
        fetch_orchestrator: BivFetchOrchestrator | None = None
        extraction_ctx = ExtractionRunContext()
        if run_id is not None:
            fetch_orchestrator = BivFetchOrchestrator(
                self._session,
                self._settings,
                run_id=run_id,
                correlation_id=correlation_id,
                metrics=pipeline_metrics,
            )
        if progress:
            progress.advance(BivPipelineStage.DECOMPOSING_QUERIES)
        executed_plan_items: list = []
        coverage_plan = build_initial_coverage_plan(inp)
        coverage_tracker = CoverageAttemptTracker()
        audit_ids: list[UUID] = []
        source_summaries: list[BusinessIdeaValidationSourceSummary] = []
        evidence_summaries: list[BusinessIdeaValidationEvidenceSummary] = []
        seen_urls: set[str] = set()
        seen_publisher_roots: set[str] = set()
        claim_pairs: list[tuple[str, str]] = []
        searched_categories: set[str] = set()
        search_calls = 0
        fetch_calls = 0
        rounds_completed = 0

        await self._prepare_investigation(inp)
        inv_id = self._cached_investigation_id
        assert inv_id is not None

        max_search_calls, max_fetch_calls = _research_budgets(self._settings)

        categories_this_round = [item.category for item in plan_items]
        coverage_plan = mark_categories_searching(coverage_plan, categories_this_round)

        for item in plan_items:
            if search_calls >= max_search_calls:
                break
            executed_plan_items.append(item)
            category = normalize_category(item.category)
            phase_stage = _PHASE_TO_PROGRESS.get(item.pipeline_phase)
            if progress and phase_stage:
                progress.advance(phase_stage)
            coverage_tracker.record_query(category, item.query)
            try:
                search_result, search_audit_id = await self._mcp.invoke_search(
                    owner_id=inp.tenant_id,
                    user_request_id=inp.user_request_id,
                    investigation_id=inv_id,
                    query=item.query,
                    limit=4,
                )
            except InvalidStateError as exc:
                if observability:
                    observability.record_provider_error(f"search:{exc}")
                pipeline_metrics.record_search_executed(success=False, candidates=0)
                continue
            search_calls += 1
            pipeline_metrics.record_search_executed(
                success=True,
                candidates=len(search_result.candidates),
            )
            audit_ids.append(search_audit_id)
            searched_categories.add(category)

            query_id = hashlib.sha256(f"{category}:{item.query}".encode()).hexdigest()[:16]
            fetched_for_category = 0
            category_had_relevant = False

            def _publisher_priority(candidate_url: str) -> tuple[int, int]:
                root = domain_from_url(candidate_url) or ""
                if root and root not in seen_publisher_roots:
                    return (0, 0)
                return (1, 0)

            ordered_candidates = sorted(
                search_result.candidates,
                key=lambda c: _publisher_priority(normalize_url(c.url) or ""),
            )

            for candidate in ordered_candidates:
                if fetch_calls >= max_fetch_calls:
                    break
                url = normalize_url(candidate.url)
                if not url:
                    continue
                if url in seen_urls:
                    pipeline_metrics.register_unique_url(duplicate=True)
                    continue
                seen_urls.add(url)
                pipeline_metrics.register_unique_url()

                if fetch_orchestrator is not None:
                    async def _mcp_fetch(url: str = url):
                        return await self._mcp.invoke_fetch(
                            owner_id=inp.tenant_id,
                            user_request_id=inp.user_request_id,
                            investigation_id=inv_id,
                            url=url,
                        )

                    fetch_outcome = await fetch_orchestrator.fetch_url(
                        url,
                        query_id=query_id,
                        mcp_fetch=_mcp_fetch,
                    )
                    if not fetch_outcome.success:
                        if observability:
                            observability.record_provider_error(
                                f"fetch:{fetch_outcome.outcome.value}"
                            )
                        continue
                    fetch_result = fetch_outcome.fetch_result
                    fetch_audit_id = fetch_outcome.audit_id
                    body = sanitize_source_body(fetch_outcome.extracted_text)
                    title = fetch_outcome.title or (
                        fetch_result.candidate.title if fetch_result and fetch_result.candidate else candidate.title
                    )
                    if fetch_outcome.extraction and fetch_outcome.extraction.extraction_status != ExtractionStatus.ACCEPTED:
                        continue
                else:
                    try:
                        fetch_result, fetch_audit_id = await self._mcp.invoke_fetch(
                            owner_id=inp.tenant_id,
                            user_request_id=inp.user_request_id,
                            investigation_id=inv_id,
                            url=url,
                        )
                    except InvalidStateError as exc:
                        if observability:
                            observability.record_provider_error(f"fetch:{exc}")
                        continue
                    raw_body = fetch_result.normalized_text_excerpt or ""
                    extracted = extract_and_normalize_document(
                        raw_body,
                        source_url=url,
                        header_content_type="text/markdown",
                        title_hint=fetch_result.candidate.title if fetch_result.candidate else candidate.title,
                        run_context=extraction_ctx,
                    )
                    pipeline_metrics.record_extraction(
                        success=extracted.extraction_status == ExtractionStatus.ACCEPTED,
                        boilerplate_rejected=extracted.rejection_reason is not None
                        and "boilerplate" in (extracted.rejection_reason.value if extracted.rejection_reason else ""),
                    )
                    if extracted.extraction_status != ExtractionStatus.ACCEPTED:
                        continue
                    body = extracted.clean_text
                    title = extracted.title or (
                        fetch_result.candidate.title if fetch_result.candidate else candidate.title
                    )

                fetch_calls += 1
                if fetch_audit_id:
                    audit_ids.append(fetch_audit_id)

                if fetch_orchestrator is None:
                    pipeline_metrics.record_extraction(success=len(body.strip()) >= 80)
                if len(body.strip()) < 80:
                    continue
                quality = classify_source(
                    url=url,
                    domain=urlparse(url).netloc or None,
                    title=title or "",
                    body_excerpt=body,
                )
                relevance = assess_source_relevance(
                    inp=inp,
                    url=url,
                    title=title or "",
                    body_excerpt=body,
                    source_class=quality.source_class,
                )
                if not relevance.relevant:
                    coverage_tracker.record_fetch(category, relevant=False, low_quality=False)
                    continue

                coverage_tracker.record_fetch(category, relevant=True, low_quality=False)
                category_had_relevant = True
                publisher_root = domain_from_url(url)
                if publisher_root:
                    seen_publisher_roots.add(publisher_root)

                source_row = await self._register_source(
                    inp=inp,
                    url=url,
                    title=title,
                    body=body,
                    category=category,
                    search_audit_id=search_audit_id,
                    fetch_audit_id=fetch_audit_id,
                    source_class=quality.source_class.value,
                )
                if source_row is None:
                    continue

                now = utc_now()
                source_summaries.append(
                    BusinessIdeaValidationSourceSummary(
                        source_id=source_row.id,
                        url=url,
                        title=source_row.title,
                        publisher=source_row.publisher,
                        domain=source_row.domain,
                        published_at=source_row.published_at,
                        retrieved_at=now,
                        source_type=SourceType(source_row.source_type),
                        status=SourceStatus(source_row.status),
                        mcp_server_role="web_fetch_mcp",
                        mcp_tool_name="fetch",
                        content_hash=source_row.content_hash,
                        source_class=quality.source_class,
                        independence_group=quality.independence_group,
                        reliability_rationale=quality.reliability_rationale,
                        research_category=category,
                    )
                )

                claims = extract_claims(body, category)
                category_low_quality = True
                for claim in claims:
                    observation = sanitize_evidence_statement(claim)
                    accepted, rejection = validate_evidence_acceptance(
                        observation=observation,
                        source_url=url,
                        source_title=source_row.title,
                    )
                    if not accepted:
                        continue
                    classification, tier, limitations = classify_evidence_item(
                        quality=quality,
                        relevance=relevance,
                        observation=observation,
                    )
                    if classification == BivEvidenceClassification.UNSUPPORTED_CLAIM:
                        continue
                    category_low_quality = False
                    if not observation:
                        continue

                    commercial = assess_commercial_relevance(
                        inp=inp,
                        category=category,
                        observation=observation,
                    )
                    if not commercial.relevant:
                        limitations = list(limitations) + [commercial.rationale]
                        continue

                    ev_row = None
                    if classification == BivEvidenceClassification.CONFIRMED:
                        ev_row = await self._create_classified_evidence(
                            inp=inp,
                            source_id=source_row.id,
                            category=category,
                            claim=observation,
                            excerpt=observation,
                            url=url,
                            title=source_row.title,
                            reliability_score=quality.reliability_score,
                            confirmed=True,
                        )
                    elif classification == BivEvidenceClassification.HYPOTHESIS:
                        ev_row = await self._create_classified_evidence(
                            inp=inp,
                            source_id=source_row.id,
                            category=category,
                            claim=observation,
                            excerpt=observation,
                            url=url,
                            title=source_row.title,
                            reliability_score=quality.reliability_score,
                            confirmed=False,
                        )

                    evidence_id = ev_row.id if ev_row is not None else uuid4()
                    if ev_row is not None:
                        claim_pairs.append((observation, url))

                    if classification == BivEvidenceClassification.CONFIRMED:
                        coverage_tracker.record_evidence(category, confirmed=True)
                    elif classification == BivEvidenceClassification.HYPOTHESIS:
                        coverage_tracker.record_evidence(category, confirmed=False, hypothesis=True)

                    evidence_type = _structured_evidence_type(category, classification)
                    source_ref = BivSourceReference(
                        source_id=source_row.id,
                        title=source_row.title,
                        domain=domain_from_url(url),
                        publisher=source_row.publisher,
                        published_at=source_row.published_at,
                        retrieved_at=now,
                    )
                    evidence_summaries.append(
                        BusinessIdeaValidationEvidenceSummary(
                            evidence_id=evidence_id,
                            source_id=source_row.id,
                            category=category,
                            evidence_type=evidence_type,
                            classification=classification,
                            claim=observation,
                            observation=observation,
                            inference=None,
                            supporting_excerpt=observation[:500],
                            source_reference=source_ref,
                            source_url=url,
                            source_title=source_row.title,
                            publisher=source_row.publisher,
                            published_at=source_row.published_at,
                            retrieved_at=now,
                            relevance_score=relevance.score,
                            reliability_score=quality.reliability_score,
                            freshness_score=0.7,
                            source_quality_tier=tier,
                            contradiction_status="none",
                            limitations=limitations,
                            sanitized=True,
                            is_search_snippet=False,
                            mcp_server_role="web_fetch_mcp",
                            mcp_tool_name="fetch",
                        )
                    )

                fetched_for_category += 1
                await self._mark_stage(inp, category)
                if fetched_for_category >= FETCHES_PER_CATEGORY:
                    break

        rounds_completed = len(phases_completed(executed_plan_items)) or 1
        findings = build_findings(evidence_summaries, inp=inp)
        risks = build_risks(evidence_summaries)
        audience_evidence = [
            e for e in evidence_summaries if normalize_category(e.category) == "audience"
        ]
        audience = run_audience_segmentation(inp, audience_evidence)
        coverage_plan = update_coverage_plan(
            coverage_plan.model_copy(update={"research_rounds_completed": rounds_completed}),
            sources=source_summaries,
            evidence=evidence_summaries,
            findings=findings,
            risks=risks,
            audience=audience,
            searched_categories=searched_categories,
        )

        findings = build_findings(evidence_summaries, inp=inp)
        hypothesis_findings = build_hypothesis_findings(evidence_summaries)
        risks = build_risks(evidence_summaries)
        opportunities = build_opportunities(findings)
        audience_evidence = [
            e for e in confirmed_evidence(evidence_summaries)
            if normalize_category(e.category) == "audience"
        ]
        audience = run_audience_segmentation(inp, audience_evidence)
        coverage_plan = update_coverage_plan(
            coverage_plan.model_copy(update={"research_rounds_completed": rounds_completed}),
            sources=source_summaries,
            evidence=confirmed_evidence(evidence_summaries),
            findings=findings,
            risks=risks,
            audience=audience,
            searched_categories=searched_categories,
        )
        contradiction_count = detect_contradiction_pairs(claim_pairs)
        gate = evaluate_coverage_gate(
            inp=inp,
            sources=source_summaries,
            evidence=confirmed_evidence(evidence_summaries),
            findings=findings,
            risks=risks,
            audience=audience,
            coverage_plan=coverage_plan,
        )
        confidence = calculate_confidence(
            sources=source_summaries,
            evidence=confirmed_evidence(evidence_summaries),
            contradiction_count=contradiction_count,
            unresolved_assumption_count=len(gate.limitations) + len(audience.limitations),
            gate_passed=gate.passed,
        )
        verdict_kind = resolve_verdict_kind(
            gate_passed=gate.passed,
            confidence=confidence,
            risk_count=len(risks),
            contradiction_count=contradiction_count,
        )
        if verdict_kind == BusinessIdeaValidationVerdictKind.PROCEED and not positive_verdict_allowed(
            gate_passed=gate.passed,
            sources=source_summaries,
            evidence=confirmed_evidence(evidence_summaries),
        ):
            verdict_kind = BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE
        if verdict_kind == BusinessIdeaValidationVerdictKind.PROCEED and not gate.passed:
            verdict_kind = BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE

        terminal_state = (
            BivResearchTerminalState.SUCCEEDED_COMPLETE
            if gate.passed and len(confirmed_evidence(evidence_summaries)) >= 3
            else BivResearchTerminalState.SUCCEEDED_INSUFFICIENT
        )

        business_verdict_id = None
        if confirmed_evidence(evidence_summaries) and gate.passed:
            business_verdict_id = await self._persist_business_verdict(
                inp=inp,
                verdict_kind=verdict_kind,
                confidence=confidence,
                evidence_summaries=confirmed_evidence(evidence_summaries),
                findings=findings,
                risks=risks,
            )

        research_gaps = build_research_gaps(evidence_summaries, gate.limitations)
        if len(confirmed_evidence(evidence_summaries)) < 3:
            research_gaps.append("fewer_than_3_confirmed_evidence")
        gap_codes = dedupe_research_gaps(list(research_gaps))
        if business_verdict_id is None:
            gap_codes.append("business_verdict_missing")
        research_gap_items = attach_semantic_groups_to_gaps(present_research_gaps(gap_codes))

        all_plan = executed_plan_items
        if contradiction_count > 0:
            for cat in ("market", "demand"):
                coverage_tracker.mark_conflict(cat)
        category_coverage = build_category_coverage(
            inp=inp,
            tracker=coverage_tracker,
            plan_items=all_plan,
        )
        all_findings = findings + hypothesis_findings
        partial_report = build_partial_report(
            inp=inp,
            findings=all_findings,
            evidence=evidence_summaries,
            gate_passed=gate.passed,
            category_coverage=category_coverage,
        )
        stop_reason = build_research_stop_reason(
            inp=inp,
            gate_passed=gate.passed,
            limitations=gate.limitations,
            sources=source_summaries,
            category_coverage=category_coverage,
            mcp_search_calls=search_calls,
        )
        remediation_questions = build_remediation_questions(category_coverage)
        semantic_gap_groups = build_semantic_gap_groups(
            category_coverage=category_coverage,
            gap_items=research_gap_items,
            remediation_questions=remediation_questions,
        )
        phases_executed = phases_completed(executed_plan_items)

        if progress:
            progress.advance(BivPipelineStage.VALIDATING_SOURCES)
            progress.advance(BivPipelineStage.EXTRACTING_EVIDENCE)
            progress.advance(BivPipelineStage.SYNTHESIZING_FINDINGS)
            progress.advance(BivPipelineStage.CALCULATING_CONFIDENCE)
            progress.advance(BivPipelineStage.CALCULATING_COVERAGE)
            progress.advance(BivPipelineStage.GENERATING_VERDICT)

        evidence_items = build_evidence_items(evidence_summaries)
        accepted_evidence_items = [e for e in evidence_items if e.accepted]
        finding_items = build_finding_items(all_findings, evidence_items)
        for item in evidence_items:
            pipeline_metrics.record_evidence(
                category=item.category or "unknown",
                accepted=item.accepted,
                rejection_reason=item.rejection_reason,
            )
        floor_statuses = evaluate_category_floors(evidence_items)
        pipeline_metrics.set_evidence_coverage(count_floors_met(floor_statuses))
        for finding in finding_items:
            pipeline_metrics.record_finding(with_evidence=bool(finding.evidence_ids))
        if pipeline_metrics.data.reasoning.findings_count:
            pipeline_metrics.set_citation_coverage(
                pipeline_metrics.data.reasoning.findings_with_evidence
                / pipeline_metrics.data.reasoning.findings_count
            )
        pipeline_metrics.set_contradiction_count(contradiction_count)

        pre_report_output = BusinessIdeaValidationOutput(
            investigation_id=inv_id,
            business_verdict_id=business_verdict_id,
            research_plan=all_plan,
            sources=source_summaries,
            evidence=evidence_summaries,
            findings=all_findings,
            verdict=verdict_kind,
            confidence=confidence,
            mcp_search_calls=search_calls,
            mcp_fetch_calls=fetch_calls,
            evidence_items=evidence_items,
            finding_items=finding_items,
        )
        pre_gate = validate_pipeline(
            pre_report_output,
            pipeline_metrics.data,
            hard_min_fetch_success_rate=self._settings.biv_pipeline_hard_min_fetch_success_rate,
            require_customer_report=False,
        )
        if not pre_gate.passed and pre_gate.failure is not None:
            partial = await self._try_partial_research_delivery(
                pre_gate,
                build_ctx=self._partial_research_context(
                    investigation_id=inv_id,
                    partial_report=partial_report,
                    evidence_items=evidence_items,
                    finding_items=finding_items,
                    sources=source_summaries,
                    evidence=evidence_summaries,
                    findings=all_findings,
                    risks=risks,
                    opportunities=opportunities,
                    research_plan=all_plan,
                    coverage_plan=coverage_plan,
                    research_gaps=gap_codes,
                    research_gap_items=research_gap_items,
                    semantic_gap_groups=semantic_gap_groups,
                    remediation_questions=remediation_questions,
                    category_coverage=category_coverage,
                    research_stop_reason=stop_reason,
                    confidence=confidence,
                    limitations=gate.limitations + audience.limitations,
                    mcp_search_calls=search_calls,
                    mcp_fetch_calls=fetch_calls,
                    research_rounds_completed=rounds_completed,
                    tool_call_audit_ids=audit_ids,
                    audience_segmentation=audience,
                    run_progress=progress.snapshot() if progress else None,
                ),
                observability=observability,
                pipeline_metrics=pipeline_metrics,
                run_id=run_id,
            )
            if partial is not None:
                return partial
            await self._raise_pipeline_failure(
                pre_gate,
                observability=observability,
                pipeline_metrics=pipeline_metrics,
                run_id=run_id,
            )

        confirmed_count = len(accepted_evidence_items)
        commercial_kind = map_legacy_verdict_kind(
            verdict_kind,
            gate_passed=gate.passed,
            confidence=confidence.total_score,
            confirmed_count=confirmed_count,
        )
        commercial_kind, _floor_blockers = apply_floor_verdict_constraints(
            commercial_kind,
            floor_statuses,
        )
        unconfirmed_topics = [
            item.customer_message for item in research_gap_items[:6]
        ] or gate.limitations[:6]
        commercial_verdict = build_commercial_verdict(
            kind=commercial_kind,
            confidence=confidence.total_score,
            findings=findings,
            risks=risks,
            unconfirmed_topics=unconfirmed_topics,
            gate_passed=gate.passed,
        )

        if progress:
            progress.advance(BivPipelineStage.BUILDING_REPORT)

        customer_report = build_customer_research_report(
            inp=inp,
            findings=findings,
            evidence=evidence_summaries,
            risks=risks,
            category_coverage=category_coverage,
            plan_items=all_plan,
            confidence=confidence,
            gate_passed=gate.passed,
            verdict=verdict_kind,
            phases_executed=phases_executed,
        )
        final_output = BusinessIdeaValidationOutput(
            investigation_id=inv_id,
            business_verdict_id=business_verdict_id,
            research_plan=all_plan,
            sources=source_summaries,
            evidence=evidence_summaries,
            findings=all_findings,
            verdict=verdict_kind,
            confidence=confidence,
            mcp_search_calls=search_calls,
            mcp_fetch_calls=fetch_calls,
            evidence_items=evidence_items,
            finding_items=finding_items,
            customer_report=customer_report,
            commercial_verdict=commercial_verdict,
        )
        final_gate = validate_pipeline(
            final_output,
            pipeline_metrics.data,
            hard_min_fetch_success_rate=self._settings.biv_pipeline_hard_min_fetch_success_rate,
            require_customer_report=True,
        )
        report_validation = validate_customer_report(final_output, pipeline_metrics.data)
        pipeline_metrics.set_report_validation(
            generated=customer_report is not None,
            passed=final_gate.passed and report_validation.passed,
            empty_links=sum(1 for e in report_validation.blocking_errors if "empty_url" in e),
            raw_dom=sum(1 for e in report_validation.blocking_errors if "raw_dom" in e),
            unsupported=sum(1 for e in report_validation.errors if "finding_without_evidence" in e),
            export_passed=report_validation.passed,
        )
        if not final_gate.passed or not report_validation.passed:
            failure_gate = final_gate
            if failure_gate.passed or failure_gate.failure is None:
                primary = (
                    report_validation.blocking_errors[0]
                    if report_validation.blocking_errors
                    else (report_validation.errors[0] if report_validation.errors else "report_validation_failed")
                )
                failure_gate = PipelineValidationResult(
                    passed=False,
                    failure=BivPipelineFailure(
                        failure_stage="report",
                        failure_code=primary.split(":")[0],
                        retryable=False,
                        safe_message="Отчёт не прошёл проверку качества.",
                    ),
                    blockers=report_validation.blocking_errors + report_validation.errors,
                )
            partial = await self._try_partial_research_delivery(
                failure_gate,
                build_ctx=self._partial_research_context(
                    investigation_id=inv_id,
                    partial_report=partial_report,
                    evidence_items=evidence_items,
                    finding_items=finding_items,
                    sources=source_summaries,
                    evidence=evidence_summaries,
                    findings=all_findings,
                    risks=risks,
                    opportunities=opportunities,
                    research_plan=all_plan,
                    coverage_plan=coverage_plan,
                    research_gaps=gap_codes,
                    research_gap_items=research_gap_items,
                    semantic_gap_groups=semantic_gap_groups,
                    remediation_questions=remediation_questions,
                    category_coverage=category_coverage,
                    research_stop_reason=stop_reason,
                    confidence=confidence,
                    limitations=gate.limitations + audience.limitations,
                    mcp_search_calls=search_calls,
                    mcp_fetch_calls=fetch_calls,
                    research_rounds_completed=rounds_completed,
                    tool_call_audit_ids=audit_ids,
                    audience_segmentation=audience,
                    run_progress=progress.snapshot() if progress else None,
                ),
                observability=observability,
                pipeline_metrics=pipeline_metrics,
                run_id=run_id,
            )
            if partial is not None:
                return partial
            await self._raise_pipeline_failure(
                failure_gate,
                observability=observability,
                pipeline_metrics=pipeline_metrics,
                run_id=run_id,
            )

        internal_diagnostics = build_internal_research_diagnostics(
            plan_items=all_plan,
            raw_research_gaps=gap_codes,
            raw_limitations=gate.limitations + audience.limitations,
            category_coverage=category_coverage,
            confidence=confidence,
            phases_executed=phases_executed,
            mcp_search_calls=search_calls,
            mcp_fetch_calls=fetch_calls,
            research_rounds_completed=rounds_completed,
            tool_call_audit_ids=audit_ids,
            evidence=evidence_summaries,
            sources=source_summaries,
            stop_reason=stop_reason,
            coverage_plan=coverage_plan,
            partial_report=partial_report,
            gap_items=research_gap_items,
            pipeline_metrics=pipeline_metrics.data,
        )

        await self._investigations.submit_review(inp.tenant_id, inp.project_id, inv_id)

        if observability:
            observability.record_transition("running", stage="pipeline_finalize")
            observability.increment("search_count", search_calls)
            observability.increment("fetch_count", fetch_calls)
            observability.increment("accepted_sources_count", len(accepted_evidence_items))
            observability.increment(
                "rejected_sources_count",
                max(0, len(evidence_items) - len(accepted_evidence_items)),
            )
            ledger_count = 0
            if run_id is not None:
                from app.db.repositories.biv_fetch_ledger import BivFetchLedgerRepository

                ledger_count = len(await BivFetchLedgerRepository(self._session).list_for_run(run_id))
            observability.attach_pipeline_metrics(pipeline_metrics.data, fetch_ledger_count=ledger_count)
            coverage_pct = 0
            if category_coverage:
                researched = sum(
                    1 for c in category_coverage if c.coverage_status.value != "not_researched"
                )
                coverage_pct = int((researched / len(category_coverage)) * 100)
            obs_snapshot = observability.snapshot()
            observability.set_final(
                confidence=confidence.total_score,
                coverage=coverage_pct,
                verdict=commercial_kind,
                export_status="ready" if customer_report else "missing",
                total_latency_ms=int(
                    (utc_now() - obs_snapshot.started_at).total_seconds() * 1000
                ),
            )

        run_progress_snapshot = progress.snapshot() if progress else None
        if progress:
            progress.advance(BivPipelineStage.COMPLETED)

        return BusinessIdeaValidationOutput(
            investigation_id=inv_id,
            business_verdict_id=business_verdict_id,
            research_terminal_state=terminal_state,
            research_gaps=gap_codes,
            research_gap_items=research_gap_items,
            semantic_gap_groups=semantic_gap_groups,
            remediation_questions=remediation_questions,
            category_coverage=category_coverage,
            research_stop_reason=stop_reason,
            partial_report=partial_report,
            research_plan=all_plan,
            coverage_plan=coverage_plan,
            audience_segmentation=audience,
            sources=source_summaries,
            evidence=evidence_summaries,
            findings=all_findings,
            risks=risks,
            opportunities=opportunities,
            verdict=verdict_kind,
            confidence=confidence,
            limitations=gate.limitations + audience.limitations,
            next_steps=default_next_steps(verdict_kind),
            tool_call_audit_ids=audit_ids,
            research_rounds_completed=rounds_completed,
            mcp_search_calls=search_calls,
            mcp_fetch_calls=fetch_calls,
            customer_report=customer_report,
            internal_diagnostics=internal_diagnostics,
            evidence_items=evidence_items,
            finding_items=finding_items,
            commercial_verdict=commercial_verdict,
            run_progress=run_progress_snapshot,
        )

    @staticmethod
    def _partial_research_context(**kwargs: Any) -> PartialResearchBuildContext:
        return PartialResearchBuildContext(**kwargs)

    async def _try_partial_research_delivery(
        self,
        gate_result: PipelineValidationResult,
        *,
        build_ctx: PartialResearchBuildContext,
        observability: BivRunObservabilityRecorder | None,
        pipeline_metrics: BivPipelineMetricsRecorder,
        run_id: UUID | None,
    ) -> BusinessIdeaValidationOutput | None:
        failure = gate_result.failure
        if failure is None or gate_result.passed:
            return None
        if not can_deliver_partial_research(
            failure.failure_code,
            metrics=pipeline_metrics.data,
            partial_report=build_ctx.partial_report,
            evidence_items=build_ctx.evidence_items,
            finding_items=build_ctx.finding_items,
        ):
            return None

        ledger_count = 0
        if run_id is not None:
            from app.db.repositories.biv_fetch_ledger import BivFetchLedgerRepository

            ledger_count = len(await BivFetchLedgerRepository(self._session).list_for_run(run_id))
        if observability:
            observability.attach_pipeline_metrics(pipeline_metrics.data, fetch_ledger_count=ledger_count)
            observability.set_pipeline_failure(failure)
            observability.record_transition("failed", stage=failure.failure_stage)

        return build_partial_research_output(
            build_ctx,
            failure_code=failure.failure_code,
            safe_message=failure.safe_message,
        )

    async def _raise_pipeline_failure(
        self,
        gate_result,
        *,
        observability: BivRunObservabilityRecorder | None,
        pipeline_metrics: BivPipelineMetricsRecorder,
        run_id: UUID | None,
    ) -> None:
        failure = gate_result.failure
        assert failure is not None
        ledger_count = 0
        if run_id is not None:
            from app.db.repositories.biv_fetch_ledger import BivFetchLedgerRepository

            ledger_count = len(await BivFetchLedgerRepository(self._session).list_for_run(run_id))
        if observability:
            observability.attach_pipeline_metrics(pipeline_metrics.data, fetch_ledger_count=ledger_count)
            observability.set_pipeline_failure(failure)
            observability.record_transition("failed", stage=failure.failure_stage)
        raise ResearchPipelineError(
            failure.failure_code,
            failure_stage=failure.failure_stage,
            retryable=failure.retryable,
            safe_message=failure.safe_message,
        )

    async def _prepare_investigation(self, inp: BusinessIdeaValidationInput) -> None:
        from app.services.commercial_research_pipeline_service import (
            CommercialResearchPipelineService,
        )

        pipeline = CommercialResearchPipelineService(self._session, self._settings)
        bootstrap = await pipeline.bootstrap(inp.tenant_id, inp.user_request_id)
        inv_id = bootstrap.run.investigation_id
        self._cached_investigation_id = inv_id

        await self._investigations.mark_ready(inp.tenant_id, inp.project_id, inv_id)
        await self._investigations.start(inp.tenant_id, inp.project_id, inv_id)

    async def _mark_stage(self, inp: BusinessIdeaValidationInput, category: str) -> None:
        stage = _STAGE_MAP.get(category)
        if stage is None or self._cached_investigation_id is None:
            return
        await self._investigations.update_stage(
            inp.tenant_id,
            inp.project_id,
            self._cached_investigation_id,
            stage,
            InvestigationStageUpdateRequest(status=InvestigationStageStatus.COMPLETED),
        )

    async def _register_source(
        self,
        *,
        inp: BusinessIdeaValidationInput,
        url: str,
        title: str,
        body: str,
        category: str,
        search_audit_id: UUID,
        fetch_audit_id: UUID,
        source_class: str = "unknown",
    ) -> SourceTable | None:
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        domain = urlparse(url).netloc or None
        inv_id = self._cached_investigation_id
        if inv_id is None:
            return None
        request = SourceCreateRequest(
            source_type=SourceType.WEBSITE,
            provenance_type=SourceProvenanceType.SECONDARY,
            title=sanitize_text(title or domain or url)[:500] or url[:200],
            origin="mcp_fetch",
            url=url,
            domain=domain,
            publisher=domain,
            accessed_at=utc_now(),
            content_hash=content_hash,
            capabilities=[SourceCapability.WEBPAGE, SourceCapability.TEXT],
            metadata={
                "mcp_search_audit_id": str(search_audit_id),
                "mcp_fetch_audit_id": str(fetch_audit_id),
                "research_category": category,
                "source_class": source_class,
            },
            attach_to_investigation_id=inv_id,
            link_purpose=f"business_idea_validation:{category}",
        )
        try:
            return await self._sources.register(inp.tenant_id, inp.project_id, request)
        except InvalidStateError as exc:
            if str(exc) != "duplicate_source":
                raise
            fingerprint = compute_source_fingerprint(
                project_id=inp.project_id,
                source_type=SourceType.WEBSITE,
                title=request.title,
                url=url,
                publisher=request.publisher,
                published_at=None,
                content_hash=content_hash,
            )
            existing = await self._sources._sources.find_live_by_fingerprint(  # noqa: SLF001
                inp.tenant_id,
                inp.project_id,
                fingerprint,
            )
            return existing

    async def _create_classified_evidence(
        self,
        *,
        inp: BusinessIdeaValidationInput,
        source_id: UUID,
        category: str,
        claim: str,
        excerpt: str,
        url: str,
        title: str,
        reliability_score: float = 0.65,
        confirmed: bool = True,
    ):
        inv_id = self._cached_investigation_id
        if inv_id is None:
            return None
        assessment = (
            EvidenceAssessmentState.CONFIRMED
            if confirmed
            else EvidenceAssessmentState.UNVERIFIED
        )
        create_req = EvidenceCreateRequest(
            claim=claim,
            evidence_type=EvidenceType.MARKET_SIGNAL
            if normalize_category(category) in {"market", "demand", "market_demand", "pricing"}
            else EvidenceType.COMPARISON
            if normalize_category(category) in {"competitors", "competition"}
            else EvidenceType.CUSTOMER_STATEMENT
            if normalize_category(category) in {"audience", "target_audience"}
            else EvidenceType.CONSTRAINT,
            investigation_area=_AREA_MAP.get(category, EvidenceInvestigationArea.OTHER),
            assessment_state=assessment,
            confidence_level=EvidenceConfidenceLevel.MEDIUM,
            materiality=EvidenceMateriality.HIGH
            if category == "commercial_risks"
            else EvidenceMateriality.MEDIUM,
            source_links=[
                EvidenceSourceLinkInput(
                    source_id=source_id,
                    stance=EvidenceSourceStance.SUPPORTS,
                    excerpt=excerpt[:500],
                    note=f"Fetched from {domain_from_url(url) or 'source'}",
                )
            ],
        )
        try:
            row = await self._evidence.create(
                inp.tenant_id,
                inp.project_id,
                inv_id,
                create_req,
            )
        except InvalidStateError as exc:
            if str(exc) in ("duplicate_evidence", "non_atomic_claim"):
                return None
            raise
        if row is None:
            return None
        if confirmed:
            await self._evidence.submit_review(inp.tenant_id, inp.project_id, inv_id, row.id)
            return await self._evidence.accept(
                inp.tenant_id,
                inp.project_id,
                inv_id,
                row.id,
                EvidenceReviewNoteRequest(note="CMVP.1.1 classified acceptance"),
            )
        return row

    async def _persist_business_verdict(
        self,
        *,
        inp: BusinessIdeaValidationInput,
        verdict_kind: BusinessIdeaValidationVerdictKind,
        confidence,
        evidence_summaries: list[BusinessIdeaValidationEvidenceSummary],
        findings: list,
        risks: list,
    ) -> UUID | None:
        inv_id = self._cached_investigation_id
        if inv_id is None:
            return None
        evidence_links = [
            BusinessVerdictEvidenceLinkCreate(
                evidence_id=e.evidence_id,
                evidence_version=1,
                role=BusinessVerdictEvidenceRole.SUPPORTS
                if e.category != "commercial_risks"
                else BusinessVerdictEvidenceRole.RISK_BASIS,
            )
            for e in evidence_summaries
        ]
        verdict_findings = [
            VerdictFinding(
                title=f.title,
                statement=f.statement,
                finding_type=f.finding_type,
                linked_evidence_ids=f.linked_evidence_ids,
            )
            for f in findings
        ]
        critical_risks = [
            VerdictCriticalRisk(
                title=r.title,
                description=r.description,
                severity=VerdictRiskSeverity.MEDIUM,
                probability=VerdictRiskProbability.MEDIUM,
                business_consequence=r.description[:500],
                linked_evidence_ids=r.linked_evidence_ids,
                verdict_sensitivity=VerdictSensitivity.MEDIUM,
            )
            for r in risks
        ]
        conditions = [
            VerdictCondition(
                id="local_validation",
                title="Подтвердить локальную специфику",
                required_action="Дополнить исследование локальными источниками",
                owner_role="founder",
                success_criterion="Есть подтверждение по району и трафику",
                consequence_if_unmet="Пересмотреть решение о запуске",
            )
        ]
        body = BusinessVerdictCreate(
            verdict_type=map_to_business_verdict_kind(verdict_kind),
            confidence_level=map_to_confidence_level(confidence.total_score),
            executive_conclusion=_executive_conclusion(verdict_kind),
            executive_rationale=_executive_rationale(
                verdict_kind, confidence.total_score, len(evidence_summaries)
            ),
            primary_business_implication="Оценка жизнеспособности идеи на основе подтверждённых источников.",
            recommended_next_action=default_next_steps(verdict_kind)[0].label,
            supporting_evidence_summary=(
                f"Подтверждено {len(evidence_summaries)} evidence records "
                f"из {len({e.source_id for e in evidence_summaries})} источников."
            ),
            evidence_links=evidence_links,
            conditions=conditions,
            critical_risks=critical_risks,
            findings=verdict_findings,
            prepared_by_type=BusinessVerdictPreparedByType.SYSTEM,
            prepared_by_reference=self.SKILL_CODE,
        )
        try:
            row = await self._verdicts.create(inp.tenant_id, inp.project_id, inv_id, body)
            return row.id if row else None
        except InvalidStateError:
            return None


def _structured_evidence_type(
    category: str,
    classification: BivEvidenceClassification,
) -> BivStructuredEvidenceType:
    if classification == BivEvidenceClassification.RESEARCH_GAP:
        return BivStructuredEvidenceType.RESEARCH_GAP
    if classification == BivEvidenceClassification.HYPOTHESIS:
        return BivStructuredEvidenceType.HYPOTHESIS
    if classification == BivEvidenceClassification.UNSUPPORTED_CLAIM:
        return BivStructuredEvidenceType.UNSUPPORTED_CLAIM
    mapping = {
        "market": BivStructuredEvidenceType.MARKET_SIGNAL,
        "demand": BivStructuredEvidenceType.MARKET_SIGNAL,
        "market_demand": BivStructuredEvidenceType.MARKET_SIGNAL,
        "competitors": BivStructuredEvidenceType.COMPETITOR_SIGNAL,
        "competition": BivStructuredEvidenceType.COMPETITOR_SIGNAL,
        "audience": BivStructuredEvidenceType.CUSTOMER_SIGNAL,
        "target_audience": BivStructuredEvidenceType.CUSTOMER_SIGNAL,
        "pricing": BivStructuredEvidenceType.ECONOMIC_SIGNAL,
        "commercial_risks": BivStructuredEvidenceType.RISK_SIGNAL,
        "local_context": BivStructuredEvidenceType.STRUCTURED_FACT,
    }
    return mapping.get(category, BivStructuredEvidenceType.OBSERVATION)


def _executive_conclusion(verdict: BusinessIdeaValidationVerdictKind) -> str:
    mapping = {
        BusinessIdeaValidationVerdictKind.PROCEED: "Запуск целесообразен при текущих данных.",
        BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS: "Запуск возможен с ограничениями.",
        BusinessIdeaValidationVerdictKind.REVISE: "Идею стоит доработать перед запуском.",
        BusinessIdeaValidationVerdictKind.REJECT: "Запуск не рекомендуется по текущим данным.",
        BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE: "Недостаточно подтверждённых данных для решения.",
    }
    return mapping[verdict]


def _executive_rationale(verdict: BusinessIdeaValidationVerdictKind, score: int, evidence_count: int) -> str:
    return (
        f"Verdict={verdict.value}; confidence={score}%; "
        f"accepted_evidence={evidence_count}. Решение основано только на fetched sources."
    )
