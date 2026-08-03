"""Category evidence floor targets and enforcement for commercial research."""

from __future__ import annotations

from app.business_idea_validation.evidence_validation import is_valid_source_url
from app.schemas.contracts import (
    BivCategoryFloorStatus,
    BivCommercialVerdictKind,
    BivEvidenceItem,
)

CANONICAL_EVIDENCE_FLOORS: dict[str, int] = {
    "market": 3,
    "competitors": 8,
    "audience": 6,
    "pricing": 5,
    "demand": 12,
}

CATEGORY_EVIDENCE_FLOORS: dict[str, int] = {
    **CANONICAL_EVIDENCE_FLOORS,
    "competition": 8,
    "icp": 6,
    "target_audience": 6,
    "market_demand": 12,
}


def normalize_floor_category(category: str) -> str:
    key = (category or "").strip().lower()
    aliases = {
        "competition": "competitors",
        "icp": "audience",
        "target_audience": "audience",
        "market_demand": "demand",
    }
    return aliases.get(key, key)


def floor_for_category(category: str) -> int | None:
    norm = normalize_floor_category(category)
    return CANONICAL_EVIDENCE_FLOORS.get(norm)


def _count_accepted_independent(
    items: list[BivEvidenceItem],
    category: str,
) -> tuple[int, int]:
    """Return accepted_count, independent_source_count for category."""
    norm = normalize_floor_category(category)
    accepted: list[BivEvidenceItem] = []
    for item in items:
        if not item.accepted:
            continue
        if normalize_floor_category(getattr(item, "category", "") or "") != norm:
            # evidence items may not have category — count all accepted if no category field
            pass
        if not is_valid_source_url(item.source_url):
            continue
        if not (item.excerpt or "").strip():
            continue
        if not (item.claim_supported or "").strip():
            continue
        accepted.append(item)

    # Filter by category via evidence type / claim heuristics when category not on item
    # BivEvidenceItem has no category — use evidence_items built from summaries with implicit grouping
    # Caller should pass pre-filtered or we count globally per category from evidence_by_category in metrics
    groups: set[str] = set()
    for item in accepted:
        group = (item.independence_group or item.source_url or "").strip().lower()
        if group:
            groups.add(group)
    return len(accepted), len(groups)


def evaluate_category_floors(
    evidence_items: list[BivEvidenceItem],
    *,
    attempts_by_category: dict[str, str] | None = None,
) -> list[BivCategoryFloorStatus]:
    """Evaluate canonical floors using accepted independent evidence per category."""
    attempts = attempts_by_category or {}
    by_category: dict[str, list[BivEvidenceItem]] = {k: [] for k in CANONICAL_EVIDENCE_FLOORS}

    for item in evidence_items:
        if not item.accepted:
            continue
        if not is_valid_source_url(item.source_url):
            continue
        if not (item.excerpt or "").strip():
            continue
        if not (item.claim_supported or "").strip():
            continue
        cat = normalize_floor_category(item.category or "")
        if cat in by_category:
            by_category[cat].append(item)

    statuses: list[BivCategoryFloorStatus] = []
    for category, required in CANONICAL_EVIDENCE_FLOORS.items():
        items = by_category.get(category, [])
        groups: set[str] = set()
        for item in items:
            group = (item.independence_group or item.source_url or "").strip().lower()
            if group:
                groups.add(group)
        accepted_count = len(items)
        independent = len(groups)
        met = accepted_count >= required and independent >= min(required, 1)
        status = "sufficient" if met else "insufficient"
        gap_reason = None
        impact = None
        if not met:
            gap_reason = (
                f"accepted={accepted_count}, independent={independent}, required={required}"
            )
            impact = _impact_for_category(category)
        statuses.append(
            BivCategoryFloorStatus(
                category=category,
                required_floor=required,
                accepted_count=accepted_count,
                independent_source_count=independent,
                status=status,
                attempts_summary=attempts.get(category, "queries executed; see diagnostics"),
                gap_reason=gap_reason,
                impact_on_verdict=impact,
            )
        )
    return statuses


def _impact_for_category(category: str) -> str:
    impacts = {
        "market": "Нельзя выдавать GO без подтверждения рынка.",
        "competitors": "Нельзя утверждать отсутствие конкурентов.",
        "audience": "ICP не подтверждён — вердикт ограничен.",
        "pricing": "Максимум PILOT ONLY / HOLD без ценового evidence.",
        "demand": "Positive commercial verdict запрещён без demand evidence.",
    }
    return impacts.get(category, "Категория не закрыта evidence floor.")


def apply_floor_verdict_constraints(
    kind: BivCommercialVerdictKind,
    floor_statuses: list[BivCategoryFloorStatus],
) -> tuple[BivCommercialVerdictKind, list[str]]:
    """Adjust commercial verdict kind based on floor enforcement rules."""
    blockers: list[str] = []
    by_cat = {fs.category: fs for fs in floor_statuses}

    market = by_cat.get("market")
    demand = by_cat.get("demand")
    pricing = by_cat.get("pricing")
    competitors = by_cat.get("competitors")

    if market and market.status == "insufficient" and kind == BivCommercialVerdictKind.GO:
        kind = BivCommercialVerdictKind.HOLD
        blockers.append("market_floor_blocks_go")

    if demand and demand.status == "insufficient" and kind in {
        BivCommercialVerdictKind.GO,
        BivCommercialVerdictKind.CONDITIONAL_GO,
    }:
        kind = BivCommercialVerdictKind.HOLD
        blockers.append("demand_floor_blocks_positive_verdict")

    if pricing and pricing.status == "insufficient" and kind == BivCommercialVerdictKind.GO:
        kind = BivCommercialVerdictKind.PILOT_ONLY
        blockers.append("pricing_floor_caps_pilot_only")

    if competitors and competitors.status == "insufficient":
        blockers.append("competition_floor_insufficient")

    return kind, blockers


def count_floors_met(floor_statuses: list[BivCategoryFloorStatus]) -> float:
    if not floor_statuses:
        return 0.0
    met = sum(1 for fs in floor_statuses if fs.status == "sufficient")
    return met / len(floor_statuses)
