"""Extended customer report validation — blocks garbage before persistence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.business_idea_validation.evidence_floors import evaluate_category_floors
from app.business_idea_validation.finding_traceability import validate_finding_traceability
from app.business_idea_validation.real_research_readiness import (
    validate_evidence_integrity,
    validate_export,
    validate_minimum_real_research,
)
from app.business_idea_validation.report_export import validate_export_content, build_customer_report_txt
from app.schemas.contracts import (
    BivCategoryFloorStatus,
    BivPipelineMetrics,
    BusinessIdeaValidationOutput,
)

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]{2,}$")
_DEBUG_CODE = re.compile(r"(pipeline_|fetch_|mcp_|error_code|traceback)", re.I)
_DOM_MARKERS = (
    "to main content",
    "skip to navigation",
    "<div",
    "document.getelementbyid",
    "cookie policy",
)
_FALLBACK_PHRASE = "Влияет на решение о запуске и приоритеты пилота."


@dataclass(slots=True)
class ReportValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    category_floors: list[BivCategoryFloorStatus] = field(default_factory=list)


def validate_customer_report(
    output: BusinessIdeaValidationOutput,
    metrics: BivPipelineMetrics,
    *,
    require_floors: bool = True,
) -> ReportValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    blocking: list[str] = []

    if metrics.discovery.search_success_count > 0 and metrics.fetch.fetch_success_count == 0:
        blocking.append("completed_report_with_zero_fetch")

    errors.extend(validate_minimum_real_research(output))
    errors.extend(validate_evidence_integrity(output))
    errors.extend(validate_finding_traceability(output.finding_items or [], output.evidence_items or []))

    report = output.customer_report
    if report is None:
        blocking.append("customer_report_missing")
    else:
        if output.confidence is None:
            blocking.append("confidence_without_calculation")
        elif not output.confidence.calculation_version:
            warnings.append("confidence_calculation_version_missing")

        blob_parts = [
            report.executive_summary.status_line if report.executive_summary else "",
        ]
        for finding in report.confirmed_findings or []:
            blob_parts.append(finding.headline)
            blob_parts.append(finding.explanation)
            for src in finding.sources:
                if not (src.url or "").startswith("http"):
                    blocking.append("empty_url_in_report")
                blob_parts.append(src.url or "")
        blob = " ".join(blob_parts).lower()
        if any(m in blob for m in _DOM_MARKERS):
            blocking.append("raw_dom_in_report")
        if _DEBUG_CODE.search(blob):
            blocking.append("debug_code_in_report")

        fallback_count = sum(
            1 for f in (output.finding_items or []) if _FALLBACK_PHRASE in (f.business_impact or "")
        )
        if fallback_count >= 3:
            blocking.append("duplicated_fallback_text")

        export_text = build_customer_report_txt(report=report, output=output)
        blocking.extend(validate_export(output))
        blocking.extend(validate_export_content(export_text))

        for line in export_text.splitlines():
            stripped = line.strip()
            if _SNAKE_CASE.fullmatch(stripped):
                blocking.append(f"snake_case_in_report:{stripped}")

    floor_statuses = evaluate_category_floors(output.evidence_items or [])
    if require_floors:
        for fs in floor_statuses:
            if fs.status == "insufficient":
                blocking.append(f"category_floor_insufficient:{fs.category}")
                if fs.gap_reason:
                    warnings.append(fs.gap_reason)

    metrics_evidence_cov = metrics.evidence.evidence_coverage
    if report and report.coverage and metrics_evidence_cov > 0:
        reported = report.coverage.overall_percent / 100.0
        if reported > metrics_evidence_cov + 0.25:
            blocking.append("coverage_inconsistent_with_evidence")

    if output.commercial_verdict and output.commercial_verdict.kind.value == "go":
        for fs in floor_statuses:
            if fs.category in {"market", "demand"} and fs.status == "insufficient":
                blocking.append(f"contradictory_verdict:{fs.category}")

    all_issues = errors + blocking
    return ReportValidationResult(
        passed=len(blocking) == 0 and not any(e.startswith("finding_without_evidence") for e in errors),
        errors=errors,
        warnings=warnings,
        blocking_errors=blocking,
        category_floors=floor_statuses,
    )
