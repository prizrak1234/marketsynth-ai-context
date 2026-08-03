"""RUNTIME-01C — evidence-insufficiency partial research delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.schemas.contracts import (
    AudienceSegmentationOutput,
    BivCategoryCoverageSummary,
    BivEvidenceItem,
    BivFindingItem,
    BivPartialResearchReport,
    BivPipelineMetrics,
    BivRemediationQuestion,
    BivResearchGapPresentation,
    BivResearchMode,
    BivResearchResultKind,
    BivResearchStopReason,
    BivResearchTerminalState,
    BivRunProgress,
    BivSemanticGapGroup,
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationNextStep,
    BusinessIdeaValidationOpportunity,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationResearchPlanItem,
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationSourceSummary,
    BusinessIdeaValidationVerdictKind,
    ResearchCoveragePlan,
)

EVIDENCE_INSUFFICIENCY_CODES: frozenset[str] = frozenset(
    {
        "high_impact_insufficient_sources",
        "finding_without_evidence",
        "finding_unaccepted_evidence",
        "finding_uses_rejected_evidence",
        "citation_coverage_incomplete",
    }
)

TECHNICAL_FAILURE_PREFIXES: tuple[str, ...] = (
    "pipeline_fetch",
    "pipeline_extraction",
    "pipeline_zero",
    "fetch_success_rate",
    "research_execution_interrupted",
    "raw_dom",
    "unsupported_high_impact_claims",
    "customer_report_missing",
    "report_validation",
)


def normalize_failure_code(code: str) -> str:
    return code.split(":")[0].strip()


def is_evidence_insufficiency_code(code: str) -> bool:
    return normalize_failure_code(code) in EVIDENCE_INSUFFICIENCY_CODES


def is_technical_failure_code(code: str) -> bool:
    base = normalize_failure_code(code)
    if base.startswith("pipeline_"):
        return True
    return any(base.startswith(prefix) for prefix in TECHNICAL_FAILURE_PREFIXES)


def research_phases_executed(metrics: BivPipelineMetrics | None) -> bool:
    if metrics is None:
        return False
    discovery = metrics.discovery.search_success_count > 0
    fetch = metrics.fetch.fetch_success_count > 0
    extract = metrics.extract.extraction_success_count > 0
    evidence = metrics.evidence.accepted_evidence > 0 or metrics.evidence.evidence_candidates > 0
    return discovery or fetch or extract or evidence


def has_deliverable_partial_artifact(
    *,
    partial_report: BivPartialResearchReport | None,
    evidence_items: list[BivEvidenceItem],
    finding_items: list[BivFindingItem],
) -> bool:
    if partial_report is not None:
        if partial_report.established_findings:
            return True
        if partial_report.probable_signals:
            return True
        if partial_report.interim_conclusion.strip():
            return True
    accepted = [item for item in evidence_items if item.accepted]
    if accepted:
        return True
    validated_findings = [item for item in finding_items if item.evidence_ids]
    return len(validated_findings) > 0


def can_deliver_partial_research(
    failure_code: str,
    *,
    metrics: BivPipelineMetrics | None,
    partial_report: BivPartialResearchReport | None,
    evidence_items: list[BivEvidenceItem],
    finding_items: list[BivFindingItem],
) -> bool:
    if is_technical_failure_code(failure_code):
        return False
    if not is_evidence_insufficiency_code(failure_code):
        return False
    if not research_phases_executed(metrics):
        return False
    return has_deliverable_partial_artifact(
        partial_report=partial_report,
        evidence_items=evidence_items,
        finding_items=finding_items,
    )


def is_partial_research_output(output: BusinessIdeaValidationOutput | None) -> bool:
    if output is None:
        return False
    return output.result_kind == BivResearchResultKind.PARTIAL_RESEARCH


def partial_research_next_steps(
    *,
    partial_report: BivPartialResearchReport | None,
    remediation_questions: list[BivRemediationQuestion],
    failure_code: str,
) -> list[BusinessIdeaValidationNextStep]:
    """Actionable next steps for partial delivery — never empty refusal without guidance."""
    steps: list[BusinessIdeaValidationNextStep] = []
    established = bool(partial_report and partial_report.established_findings)
    probable = bool(partial_report and partial_report.probable_signals)

    if remediation_questions:
        steps.append(
            BusinessIdeaValidationNextStep(
                id="answer_remediation",
                label="Ответить на уточняющие вопросы и повторить исследование",
                action="refine_inputs",
            ),
        )
    elif established or probable:
        steps.append(
            BusinessIdeaValidationNextStep(
                id="pilot_validate",
                label="Проверить установленные сигналы на пилоте с 5–10 клиентами",
                action="prepare_launch",
            ),
        )
        steps.append(
            BusinessIdeaValidationNextStep(
                id="narrow_segment",
                label="Сузить сегмент или географию и повторить исследование",
                action="refine_inputs",
            ),
        )
    else:
        steps.append(
            BusinessIdeaValidationNextStep(
                id="clarify_idea",
                label="Уточнить продукт, аудиторию и географию в брифе",
                action="refine_inputs",
            ),
        )
        steps.append(
            BusinessIdeaValidationNextStep(
                id="retry_research",
                label="Повторить исследование с более конкретным контекстом",
                action="revise_idea",
            ),
        )

    if normalize_failure_code(failure_code) == "high_impact_insufficient_sources":
        steps.append(
            BusinessIdeaValidationNextStep(
                id="add_sources",
                label="Добавить конкурентов, цены или локальные источники в бриф",
                action="refine_inputs",
            ),
        )
    return steps[:4]


@dataclass(slots=True)
class PartialResearchBuildContext:
    investigation_id: UUID
    partial_report: BivPartialResearchReport | None
    evidence_items: list[BivEvidenceItem]
    finding_items: list[BivFindingItem]
    sources: list[BusinessIdeaValidationSourceSummary]
    evidence: list[BusinessIdeaValidationEvidenceSummary]
    findings: list[BusinessIdeaValidationFinding]
    risks: list[BusinessIdeaValidationRisk]
    opportunities: list[BusinessIdeaValidationOpportunity]
    research_plan: list[BusinessIdeaValidationResearchPlanItem]
    coverage_plan: ResearchCoveragePlan
    research_gaps: list[str]
    research_gap_items: list[BivResearchGapPresentation]
    semantic_gap_groups: list[BivSemanticGapGroup]
    remediation_questions: list[BivRemediationQuestion]
    category_coverage: list[BivCategoryCoverageSummary]
    research_stop_reason: BivResearchStopReason | None
    confidence: BusinessIdeaValidationConfidence
    limitations: list[str]
    mcp_search_calls: int
    mcp_fetch_calls: int
    research_rounds_completed: int
    tool_call_audit_ids: list[UUID] = field(default_factory=list)
    audience_segmentation: AudienceSegmentationOutput | None = None
    run_progress: BivRunProgress | None = None
    research_mode: BivResearchMode | None = None
    parent_run_id: UUID | None = None


def build_partial_research_output(
    ctx: PartialResearchBuildContext,
    *,
    failure_code: str,
    safe_message: str,
) -> BusinessIdeaValidationOutput:
    return BusinessIdeaValidationOutput(
        investigation_id=ctx.investigation_id,
        business_verdict_id=None,
        research_terminal_state=BivResearchTerminalState.SUCCEEDED_INSUFFICIENT,
        result_kind=BivResearchResultKind.PARTIAL_RESEARCH,
        partial_failure_code=normalize_failure_code(failure_code),
        partial_safe_message=safe_message,
        research_gaps=list(ctx.research_gaps),
        research_gap_items=list(ctx.research_gap_items),
        semantic_gap_groups=list(ctx.semantic_gap_groups),
        remediation_questions=list(ctx.remediation_questions),
        category_coverage=list(ctx.category_coverage),
        research_stop_reason=ctx.research_stop_reason,
        partial_report=ctx.partial_report,
        research_plan=list(ctx.research_plan),
        coverage_plan=ctx.coverage_plan,
        audience_segmentation=ctx.audience_segmentation,
        sources=list(ctx.sources),
        evidence=list(ctx.evidence),
        findings=list(ctx.findings),
        risks=list(ctx.risks),
        opportunities=list(ctx.opportunities),
        verdict=BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        confidence=ctx.confidence,
        limitations=list(ctx.limitations),
        next_steps=partial_research_next_steps(
            partial_report=ctx.partial_report,
            remediation_questions=ctx.remediation_questions,
            failure_code=failure_code,
        ),
        tool_call_audit_ids=list(ctx.tool_call_audit_ids),
        research_rounds_completed=ctx.research_rounds_completed,
        mcp_search_calls=ctx.mcp_search_calls,
        mcp_fetch_calls=ctx.mcp_fetch_calls,
        customer_report=None,
        internal_diagnostics=None,
        research_mode=ctx.research_mode,
        parent_run_id=ctx.parent_run_id,
        evidence_items=list(ctx.evidence_items),
        finding_items=list(ctx.finding_items),
        commercial_verdict=None,
        run_progress=ctx.run_progress,
    )
