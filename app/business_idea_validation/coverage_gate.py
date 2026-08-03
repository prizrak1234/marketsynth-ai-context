"""Minimum research coverage gate — PRODUCT-01.3B.2 canonical categories."""

from __future__ import annotations

from dataclasses import dataclass

from app.business_idea_validation.audience_segmentation import audience_has_support
from app.business_idea_validation.coverage_categories import normalize_category
from app.business_idea_validation.research_plan import requires_local_context
from app.business_idea_validation.source_quality import count_independent_groups
from app.schemas.contracts import (
    AudienceSegmentationOutput,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationSourceSummary,
    ResearchCoveragePlan,
    ResearchCoverageCategoryStatus,
)


@dataclass(frozen=True, slots=True)
class CoverageGateResult:
    passed: bool
    limitations: list[str]


def _normalized_categories(items: list, attr: str = "category") -> set[str]:
    return {normalize_category(getattr(i, attr)) for i in items}


def evaluate_coverage_gate(
    *,
    inp: BusinessIdeaValidationInput,
    sources: list[BusinessIdeaValidationSourceSummary],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    findings: list[BusinessIdeaValidationFinding],
    risks: list[BusinessIdeaValidationRisk],
    audience: AudienceSegmentationOutput | None,
    coverage_plan: ResearchCoveragePlan | None = None,
) -> CoverageGateResult:
    limitations: list[str] = []

    independent_groups = count_independent_groups(sources)
    if len(sources) < 3:
        limitations.append("fewer_than_3_fetched_sources")
    if len(independent_groups) < 3:
        limitations.append("fewer_than_3_independent_publishers")
    if len(evidence) < 3:
        limitations.append("fewer_than_3_evidence_records")

    categories = _normalized_categories(findings)
    evidence_categories = _normalized_categories(evidence)

    if "market" not in categories and "market" not in evidence_categories:
        limitations.append("missing_market_finding")
    if "competitors" not in categories and "competitors" not in evidence_categories:
        limitations.append("missing_competitor_finding")
    if "demand" not in categories and "demand" not in evidence_categories:
        limitations.append("missing_demand_finding")
    if "pricing" not in categories and "pricing" not in evidence_categories:
        if not (inp.pricing_or_revenue_model or inp.budget or "").strip():
            limitations.append("missing_pricing_finding")

    audience_ok = audience_has_support(audience or AudienceSegmentationOutput(), [
        e for e in evidence if normalize_category(e.category) == "audience"
    ])
    if not audience_ok:
        limitations.append("missing_audience_finding")

    if not risks and "commercial_risks" not in evidence_categories:
        limitations.append("missing_risk_finding")

    if requires_local_context(inp):
        if "local_context" not in categories and "local_context" not in evidence_categories:
            limitations.append("missing_local_context")

    passed = (
        len(sources) >= 3
        and len(independent_groups) >= 3
        and len(evidence) >= 3
        and ("market" in categories or "market" in evidence_categories)
        and ("competitors" in categories or "competitors" in evidence_categories)
        and ("demand" in categories or "demand" in evidence_categories)
        and audience_ok
        and (len(risks) >= 1 or "commercial_risks" in evidence_categories)
        and (
            not requires_local_context(inp)
            or "local_context" in categories
            or "local_context" in evidence_categories
        )
    )
    return CoverageGateResult(passed=passed, limitations=limitations)


def positive_verdict_allowed(
    *,
    gate_passed: bool,
    sources: list[BusinessIdeaValidationSourceSummary],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
) -> bool:
    if not gate_passed:
        return False
    groups = count_independent_groups(sources)
    if len(groups) < 3:
        return False
    if len(evidence) < 3:
        return False
    reliable = [e for e in evidence if e.reliability_score >= 0.55]
    return len(reliable) >= 2
