"""Hard pipeline validation — blocks false-positive completed runs."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.business_idea_validation.evidence_floors import (
    CATEGORY_EVIDENCE_FLOORS,
    normalize_floor_category,
)
from app.business_idea_validation.finding_traceability import validate_finding_traceability
from app.business_idea_validation.evidence_floors import evaluate_category_floors, count_floors_met
from app.business_idea_validation.real_research_readiness import (
    validate_evidence_integrity,
    validate_export,
    validate_minimum_real_research,
)
from app.schemas.contracts import (
    BivFetchOutcomeCode,
    BivPipelineFailure,
    BivPipelineMetrics,
    BusinessIdeaValidationOutput,
)


@dataclass(slots=True)
class PipelineValidationResult:
    passed: bool
    failure: BivPipelineFailure | None = None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def compute_evidence_coverage(metrics: BivPipelineMetrics) -> float:
    """Coverage = share of category floors met with accepted independent evidence."""
    by_cat = metrics.evidence.evidence_by_category
    if not CATEGORY_EVIDENCE_FLOORS:
        return 0.0
    met = 0
    total = 0
    seen_cats: set[str] = set()
    for raw_cat, floor in CATEGORY_EVIDENCE_FLOORS.items():
        cat = normalize_floor_category(raw_cat)
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        total += 1
        count = 0
        for key, val in by_cat.items():
            if normalize_floor_category(key) == cat:
                count += val
        if count >= floor:
            met += 1
    return met / total if total else 0.0


def validate_pipeline(
    output: BusinessIdeaValidationOutput,
    metrics: BivPipelineMetrics,
    *,
    hard_min_fetch_success_rate: float = 0.0,
    require_customer_report: bool = True,
) -> PipelineValidationResult:
    blockers: list[str] = []
    warnings: list[str] = []

    discovery = metrics.discovery
    fetch = metrics.fetch

    search_ok = discovery.search_success_count
    fetch_ok = fetch.fetch_success_count

    if search_ok > 0 and fetch_ok == 0:
        blockers.append("pipeline_fetch_zero_success")

    if fetch.fetch_attempts > 0 and fetch.fetch_success_rate < hard_min_fetch_success_rate:
        if hard_min_fetch_success_rate > 0:
            blockers.append(f"fetch_success_rate_below_minimum:{fetch.fetch_success_rate:.2f}")

    if fetch_ok > 0 and metrics.extract.extraction_success_count == 0:
        blockers.append("pipeline_extraction_zero_success")

    if metrics.evidence.evidence_candidates == 0 and fetch_ok > 0:
        blockers.append("pipeline_zero_evidence_candidates")

    if metrics.reasoning.findings_with_evidence == 0 and metrics.evidence.accepted_evidence > 0:
        blockers.append("pipeline_findings_without_evidence")

    citation = metrics.reasoning.citation_coverage
    if metrics.reasoning.findings_count > 0 and citation < 1.0:
        blockers.append(f"citation_coverage_incomplete:{citation:.2f}")

    blockers.extend(validate_minimum_real_research(output))
    blockers.extend(validate_evidence_integrity(output))
    blockers.extend(validate_finding_traceability(output.finding_items or [], output.evidence_items or []))

    floor_statuses = evaluate_category_floors(output.evidence_items or [])
    metrics.evidence.evidence_coverage = count_floors_met(floor_statuses)
    for fs in floor_statuses:
        if fs.status == "insufficient":
            warnings.append(f"category_floor_insufficient:{fs.category}")

    if require_customer_report:
        export_issues = (
            validate_export(output)
            if output.customer_report
            else ["customer_report_missing"]
        )
        if export_issues:
            blockers.extend(export_issues)

    if metrics.report.raw_dom_detected > 0:
        blockers.append("raw_dom_in_report")

    if metrics.report.unsupported_claims > 0:
        blockers.append("unsupported_high_impact_claims")

    coverage = compute_evidence_coverage(metrics)
    metrics.evidence.evidence_coverage = max(metrics.evidence.evidence_coverage, coverage)

    if blockers:
        primary = blockers[0]
        stage = _stage_for_code(primary)
        retryable = primary in {
            "pipeline_fetch_zero_success",
            "fetch_success_rate_below_minimum",
            "pipeline_extraction_zero_success",
        } or primary.startswith("fetch_success_rate")
        return PipelineValidationResult(
            passed=False,
            failure=BivPipelineFailure(
                failure_stage=stage,
                failure_code=primary.split(":")[0],
                retryable=retryable,
                safe_message=_safe_message(primary),
            ),
            blockers=blockers,
            warnings=warnings,
        )

    return PipelineValidationResult(passed=True, warnings=warnings)


def classify_baseline_8038e2a7(search: int, fetch_success: int) -> PipelineValidationResult:
    """Regression classifier for known incident pattern."""
    metrics = BivPipelineMetrics()
    metrics.discovery.search_success_count = search
    metrics.fetch.fetch_attempts = search
    metrics.fetch.fetch_failure_count = search - fetch_success
    metrics.fetch.fetch_success_count = fetch_success
    metrics.fetch.fetch_success_rate = fetch_success / search if search else 0.0
    from app.schemas.contracts import BusinessIdeaValidationConfidence, BusinessIdeaValidationVerdictKind

    output = BusinessIdeaValidationOutput(
        investigation_id=__import__("uuid").uuid4(),
        verdict=BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        mcp_search_calls=search,
        mcp_fetch_calls=fetch_success,
        confidence=BusinessIdeaValidationConfidence(total_score=10),
    )
    return validate_pipeline(output, metrics)


def _stage_for_code(code: str) -> str:
    if code.startswith("pipeline_fetch") or code.startswith("fetch_"):
        return "fetch"
    if code.startswith("pipeline_extraction") or "extract" in code:
        return "extract"
    if "evidence" in code:
        return "evidence"
    if "citation" in code or "finding" in code:
        return "reasoning"
    if "export" in code or "dom" in code or "report" in code:
        return "report"
    return "pipeline"


def _safe_message(code: str) -> str:
    messages = {
        "pipeline_fetch_zero_success": (
            "Поиск нашёл источники, но ни одна страница не была успешно загружена. "
            "Исследование не может быть завершено без документов."
        ),
        "pipeline_extraction_zero_success": (
            "Страницы загружены, но текст не удалось извлечь для анализа."
        ),
        "pipeline_zero_evidence_candidates": (
            "Не удалось сформировать доказательства из загруженных источников."
        ),
        "citation_coverage_incomplete": (
            "Не все выводы связаны с подтверждёнными доказательствами."
        ),
    }
    base = code.split(":")[0]
    return messages.get(base, "Исследование не прошло проверку качества pipeline.")
