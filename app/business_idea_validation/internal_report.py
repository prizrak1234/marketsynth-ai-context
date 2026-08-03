"""CWF.1 — internal / debug research diagnostics."""

from __future__ import annotations

from app.schemas.contracts import (
    BivInternalResearchDiagnostics,
    BivPartialResearchReport,
    BivPipelineFailure,
    BivPipelineMetrics,
    BivResearchGapPresentation,
    BivResearchStopReason,
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationResearchPlanItem,
    BusinessIdeaValidationSourceSummary,
    ResearchCoveragePlan,
    BivCategoryCoverageSummary,
)
from uuid import UUID


def build_internal_research_diagnostics(
    *,
    plan_items: list[BusinessIdeaValidationResearchPlanItem],
    raw_research_gaps: list[str],
    raw_limitations: list[str],
    category_coverage: list[BivCategoryCoverageSummary],
    confidence: BusinessIdeaValidationConfidence,
    phases_executed: list[str],
    mcp_search_calls: int,
    mcp_fetch_calls: int,
    research_rounds_completed: int,
    tool_call_audit_ids: list[UUID],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    sources: list[BusinessIdeaValidationSourceSummary],
    stop_reason: BivResearchStopReason | None,
    coverage_plan: ResearchCoveragePlan,
    partial_report: BivPartialResearchReport | None,
    gap_items: list[BivResearchGapPresentation],
    pipeline_metrics: BivPipelineMetrics | None = None,
    pipeline_failure: BivPipelineFailure | None = None,
) -> BivInternalResearchDiagnostics:
    return BivInternalResearchDiagnostics(
        search_queries=plan_items,
        raw_research_gaps=raw_research_gaps,
        raw_limitations=raw_limitations,
        category_coverage_internal=category_coverage,
        confidence_calculation=confidence,
        pipeline_phases_completed=phases_executed,
        mcp_search_calls=mcp_search_calls,
        mcp_fetch_calls=mcp_fetch_calls,
        research_rounds_completed=research_rounds_completed,
        tool_call_audit_ids=tool_call_audit_ids,
        raw_evidence=evidence,
        raw_sources=sources,
        research_stop_reason_code=stop_reason.code.value if stop_reason else None,
        coverage_plan=coverage_plan,
        partial_report_internal=partial_report,
        research_gap_items_internal=gap_items,
        pipeline_metrics=pipeline_metrics,
        pipeline_failure=pipeline_failure,
    )
