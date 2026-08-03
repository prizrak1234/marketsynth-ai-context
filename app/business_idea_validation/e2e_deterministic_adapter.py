"""RUNTIME-01F — deterministic BIV outcomes for Level-1 E2E (fixture boundary only)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.business_idea_validation.e2e_deterministic_fixture import E2eDeterministicOutcome
from app.business_idea_validation.partial_research_delivery import (
    PartialResearchBuildContext,
    build_partial_research_output,
)
from app.business_idea_validation.progress_persistence import PersistingBivRunProgressTracker
from app.core.exceptions import ResearchPipelineError
from app.schemas.contracts import (
    BivEvidenceItem,
    BivFindingItem,
    BivPartialResearchReport,
    BivPipelineStage,
    BivResearchResultKind,
    BivResearchTerminalState,
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationVerdictKind,
    ResearchCoveragePlan,
)


def _accepted_evidence() -> BivEvidenceItem:
    return BivEvidenceItem(
        evidence_id=uuid4(),
        source_url="https://example.com/e2e-market-report",
        source_title="E2E market report",
        accessed_at=datetime.now(UTC),
        excerpt="Substantive market observation with enough detail for validation.",
        claim_supported="Market demand signal for E2E SaaS.",
        relevance_score=0.8,
        quality_score=0.7,
        freshness_score=0.6,
        independence_group="example.com",
        category="market",
        accepted=True,
    )


def _finding_item(evidence_id: UUID) -> BivFindingItem:
    return BivFindingItem(
        finding_id=uuid4(),
        category="market",
        claim="Demand exists in target segment",
        interpretation="Early demand signal is visible",
        business_impact="Supports pilot validation",
        evidence_ids=[evidence_id],
        confidence=0.6,
    )


def _build_verdict_output(*, run_id: UUID) -> BusinessIdeaValidationOutput:
    return BusinessIdeaValidationOutput(
        investigation_id=uuid4(),
        business_verdict_id=uuid4(),
        run_id=run_id,
        research_terminal_state=BivResearchTerminalState.SUCCEEDED_COMPLETE,
        result_kind=BivResearchResultKind.COMPLETE_RESEARCH,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
        confidence=BusinessIdeaValidationConfidence(total_score=72),
        findings=[],
        risks=[
            BusinessIdeaValidationRisk(
                title="Competition intensity",
                description="Established players may compress margins.",
                severity="medium",
            )
        ],
        limitations=["E2E deterministic fixture — not real provider research."],
        mcp_search_calls=1,
        mcp_fetch_calls=1,
        research_rounds_completed=1,
    )


def _build_partial_output(*, run_id: UUID) -> BusinessIdeaValidationOutput:
    evidence_item = _accepted_evidence()
    ctx = PartialResearchBuildContext(
        investigation_id=uuid4(),
        partial_report=BivPartialResearchReport(
            established_findings=["Рынок SaaS для малого бизнеса показывает рост"],
            interim_conclusion="Недостаточно данных для полного вердикта.",
        ),
        evidence_items=[evidence_item],
        finding_items=[_finding_item(evidence_item.evidence_id)],
        sources=[],
        evidence=[],
        findings=[],
        risks=[],
        opportunities=[],
        research_plan=[],
        coverage_plan=ResearchCoveragePlan(),
        research_gaps=["high_impact_insufficient_sources"],
        research_gap_items=[],
        semantic_gap_groups=[],
        remediation_questions=[],
        category_coverage=[],
        research_stop_reason=None,
        confidence=BusinessIdeaValidationConfidence(total_score=42),
        limitations=["Недостаточно источников высокого impact"],
        mcp_search_calls=1,
        mcp_fetch_calls=1,
        research_rounds_completed=1,
    )
    output = build_partial_research_output(
        ctx,
        failure_code="high_impact_insufficient_sources",
        safe_message="Недостаточно источников для полного вердикта.",
    )
    return output.model_copy(update={"run_id": run_id})


async def execute_e2e_deterministic_run(
    outcome: E2eDeterministicOutcome,
    _skill_input: BusinessIdeaValidationInput,
    *,
    run_id: UUID,
    progress: PersistingBivRunProgressTracker | None = None,
) -> BusinessIdeaValidationOutput:
    if progress is not None:
        progress.advance(BivPipelineStage.NORMALIZING_INPUT)
        progress.advance(BivPipelineStage.DECOMPOSING_QUERIES)
        progress.advance(BivPipelineStage.SEARCHING_DIRECT)
        await asyncio.sleep(1.5)
        progress.advance(BivPipelineStage.COMPLETED)

    if outcome == E2eDeterministicOutcome.TECHNICAL:
        raise ResearchPipelineError(
            failure_code="pipeline_fetch_failed",
            failure_stage="fetch",
            retryable=True,
            safe_message="Не удалось получить данные из источников.",
        )
    if outcome == E2eDeterministicOutcome.PARTIAL:
        return _build_partial_output(run_id=run_id)
    return _build_verdict_output(run_id=run_id)
