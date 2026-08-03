"""Research coverage matrix — CMVP.1.1 + PRODUCT-01.3B.2 canonical categories."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.business_idea_validation.coverage_categories import (
    normalize_category,
    required_categories,
)
from app.schemas.contracts import (
    AudienceSegmentationOutput,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationSourceSummary,
    ResearchCoverageCategoryItem,
    ResearchCoverageCategoryStatus,
    ResearchCoveragePlan,
)


def build_initial_coverage_plan(inp: BusinessIdeaValidationInput) -> ResearchCoveragePlan:
    categories = [_blank_category(cat) for cat in required_categories(inp)]
    return ResearchCoveragePlan(categories=categories)


def _blank_category(category: str) -> ResearchCoverageCategoryItem:
    return ResearchCoverageCategoryItem(
        category=category,
        required=True,
        status=ResearchCoverageCategoryStatus.NOT_STARTED,
    )


def update_coverage_plan(
    plan: ResearchCoveragePlan,
    *,
    sources: list[BusinessIdeaValidationSourceSummary],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    findings: list[BusinessIdeaValidationFinding],
    risks: list[BusinessIdeaValidationRisk],
    audience: AudienceSegmentationOutput | None,
    searched_categories: set[str],
) -> ResearchCoveragePlan:
    evidence_by_category: dict[str, list[UUID]] = {}
    sources_by_category: dict[str, list[UUID]] = {}
    for item in evidence:
        cat = normalize_category(item.category)
        evidence_by_category.setdefault(cat, []).append(item.evidence_id)
    for item in sources:
        category = normalize_category(item.research_category or "")
        if not category:
            continue
        sources_by_category.setdefault(category, []).append(item.source_id)

    finding_by_category = {normalize_category(f.category): f for f in findings}
    normalized_searched = {normalize_category(c) for c in searched_categories}
    updated: list[ResearchCoverageCategoryItem] = []

    for cat in plan.categories:
        canonical = normalize_category(cat.category)
        ev_ids = evidence_by_category.get(canonical, [])
        src_ids = sources_by_category.get(canonical, [])
        finding = finding_by_category.get(canonical)
        hypothesis_ids: list[str] = []
        unresolved: list[str] = list(cat.unresolved_questions)

        if canonical == "audience" and audience:
            for seg in audience.segments:
                if seg.is_hypothesis:
                    hypothesis_ids.append(seg.segment_id)
                elif seg.linked_evidence_ids:
                    ev_ids = list({*ev_ids, *seg.linked_evidence_ids})

        status = cat.status
        if canonical in normalized_searched and not ev_ids and not hypothesis_ids:
            status = ResearchCoverageCategoryStatus.INSUFFICIENT
        elif finding and ev_ids:
            status = ResearchCoverageCategoryStatus.SUPPORTED
        elif canonical == "audience" and hypothesis_ids:
            status = ResearchCoverageCategoryStatus.INSUFFICIENT
            unresolved.append("audience_supported_by_hypothesis_only")
        elif canonical == "commercial_risks" and risks:
            status = ResearchCoverageCategoryStatus.SUPPORTED
        elif ev_ids:
            status = ResearchCoverageCategoryStatus.SUPPORTED
        elif canonical in normalized_searched:
            status = ResearchCoverageCategoryStatus.INSUFFICIENT
        elif status == ResearchCoverageCategoryStatus.NOT_STARTED:
            status = ResearchCoverageCategoryStatus.NOT_STARTED

        updated.append(
            ResearchCoverageCategoryItem(
                category=canonical,
                required=cat.required,
                status=status,
                source_ids=list(dict.fromkeys(src_ids)),
                evidence_ids=list(dict.fromkeys(ev_ids)),
                finding_ids=[finding.title] if finding else [],
                hypothesis_ids=hypothesis_ids,
                unresolved_questions=unresolved,
                follow_up_queries=list(cat.follow_up_queries),
            )
        )

    groups = sorted({s.independence_group for s in sources if s.independence_group})
    return ResearchCoveragePlan(
        categories=updated,
        research_rounds_completed=plan.research_rounds_completed,
        targeted_retry_categories=list(plan.targeted_retry_categories),
        independent_source_groups=groups,
    )


def missing_categories_for_retry(plan: ResearchCoveragePlan) -> list[str]:
    missing: list[str] = []
    for cat in plan.categories:
        if not cat.required:
            continue
        if cat.status in {
            ResearchCoverageCategoryStatus.NOT_STARTED,
            ResearchCoverageCategoryStatus.INSUFFICIENT,
            ResearchCoverageCategoryStatus.SEARCHING,
        }:
            missing.append(normalize_category(cat.category))
    return missing


def mark_categories_searching(
    plan: ResearchCoveragePlan,
    categories: list[str],
) -> ResearchCoveragePlan:
    normalized = {normalize_category(c) for c in categories}
    updated: list[ResearchCoverageCategoryItem] = []
    for cat in plan.categories:
        if normalize_category(cat.category) in normalized:
            updated.append(
                cat.model_copy(update={"status": ResearchCoverageCategoryStatus.SEARCHING})
            )
        else:
            updated.append(cat)
    return plan.model_copy(update={"categories": updated})


def new_hypothesis_id(prefix: str = "aud") -> str:
    return f"{prefix}-{uuid4().hex[:8]}"
