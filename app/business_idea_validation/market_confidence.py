"""CWF.1 — dimension confidence and research coverage scoring."""

from __future__ import annotations

from app.business_idea_validation.coverage_categories import (
    CATEGORY_LABELS_RU,
    normalize_category,
    required_categories,
)
from app.schemas.contracts import (
    BivCategoryCoverageSummary,
    BivCoverageAttemptStatus,
    BivDimensionConfidenceScore,
    BivResearchCoverageScore,
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationResearchPlanItem,
)

_DIMENSIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("market_size", "Размер рынка", ("market",)),
    ("competitors", "Конкуренты", ("competitors",)),
    ("icp", "ICP", ("audience",)),
    ("economics", "Экономика", ("pricing", "demand")),
    ("regulation", "Регуляторика", ("local_context", "commercial_risks")),
    ("monetization", "Монетизация", ("pricing",)),
)

_STATUS_SCORE: dict[BivCoverageAttemptStatus, int] = {
    BivCoverageAttemptStatus.CONFIRMED: 92,
    BivCoverageAttemptStatus.NOT_CONFIRMED: 58,
    BivCoverageAttemptStatus.USER_HYPOTHESIS: 45,
    BivCoverageAttemptStatus.CONFLICTED: 40,
    BivCoverageAttemptStatus.FOUND_BUT_LOW_QUALITY: 35,
    BivCoverageAttemptStatus.FOUND_BUT_IRRELEVANT: 28,
    BivCoverageAttemptStatus.NOT_FOUND: 22,
    BivCoverageAttemptStatus.NOT_RESEARCHED: 12,
}


def _category_score(
    coverage: list[BivCategoryCoverageSummary],
    cats: tuple[str, ...],
) -> int:
    by_cat = {c.category: c for c in coverage}
    scores: list[int] = []
    for cat in cats:
        row = by_cat.get(cat)
        if row is None:
            scores.append(12)
        else:
            scores.append(_STATUS_SCORE.get(row.coverage_status, 20))
    return int(round(sum(scores) / max(len(scores), 1)))


def calculate_dimension_confidence(
    *,
    inp: BusinessIdeaValidationInput,
    category_coverage: list[BivCategoryCoverageSummary],
    evidence: list[BusinessIdeaValidationEvidenceSummary],
    market_confidence: BusinessIdeaValidationConfidence,
) -> list[BivDimensionConfidenceScore]:
    dimensions: list[BivDimensionConfidenceScore] = []
    for dim_id, label, cats in _DIMENSIONS:
        base = _category_score(category_coverage, cats)
        confirmed_in_dim = sum(
            1
            for e in evidence
            if normalize_category(e.category) in cats
            and e.classification.value == "confirmed"
        )
        boost = min(12, confirmed_in_dim * 4)
        penalty = 0 if market_confidence.total_score >= 40 else 8
        score = max(0, min(100, base + boost - penalty))
        dimensions.append(
            BivDimensionConfidenceScore(
                dimension_id=dim_id,
                label=label,
                score=score,
            )
        )
    return dimensions


def calculate_coverage_score(
    *,
    inp: BusinessIdeaValidationInput,
    category_coverage: list[BivCategoryCoverageSummary],
    plan_items: list[BusinessIdeaValidationResearchPlanItem],
    phases_executed: list[str],
) -> BivResearchCoverageScore:
    required = required_categories(inp)
    researched_labels: list[str] = []
    researched_count = 0

    by_cat = {c.category: c for c in category_coverage}
    for cat in required:
        label = CATEGORY_LABELS_RU.get(cat, cat)
        row = by_cat.get(cat)
        if row and row.coverage_status != BivCoverageAttemptStatus.NOT_RESEARCHED:
            researched_count += 1
            researched_labels.append(label)

    if plan_items:
        researched_count = max(
            researched_count,
            sum(
                1
                for cat in required
                if any(i.category == cat for i in plan_items)
            ),
        )

    phase_bonus = min(15, len(phases_executed) * 2)
    base_percent = int(round(researched_count / max(len(required), 1) * 100))
    overall = min(100, base_percent + phase_bonus // 2)

    extra = ["источники"] if researched_count > 0 else []
    return BivResearchCoverageScore(
        dimensions_researched=researched_labels + extra,
        overall_percent=overall,
    )
