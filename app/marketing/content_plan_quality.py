"""Content plan draft quality contract (Phase 5.3) — deterministic heuristics only."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

DEFAULT_CONTENT_PLAN_MIN_BODY_LENGTH = 500

CONTENT_PLAN_PURPOSE = "content_plan"

_REQUIRED_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Content plan summary",
        "has_content_plan_summary",
        ("## content plan summary", "content plan summary"),
    ),
    (
        "Funnel gaps to cover",
        "has_funnel_gaps_to_cover",
        ("## funnel gaps to cover", "funnel gaps to cover"),
    ),
    (
        "Recommended assets by funnel step",
        "has_recommended_assets_by_step",
        (
            "## recommended assets by funnel step",
            "recommended assets by funnel step",
        ),
    ),
    (
        "Priority order",
        "has_priority_order",
        ("## priority order", "priority order"),
    ),
    (
        "Production notes",
        "has_production_notes",
        ("## production notes", "production notes"),
    ),
    (
        "Risks / assumptions",
        "has_risks_assumptions",
        ("## risks", "risks / assumptions", "risks and assumptions"),
    ),
)


class MarketingContentPlanDraftQuality(BaseModel):
    has_content_plan_summary: bool = False
    has_funnel_gaps_to_cover: bool = False
    has_recommended_assets_by_step: bool = False
    has_priority_order: bool = False
    has_production_notes: bool = False
    has_risks_assumptions: bool = False
    min_body_length_met: bool = False
    score: float = 0.0
    missing_sections: list[str] = Field(default_factory=list)


def _section_present(body_lower: str, markers: tuple[str, ...]) -> bool:
    return any(marker in body_lower for marker in markers)


def evaluate_content_plan_body(
    body: str,
    *,
    min_length: int = DEFAULT_CONTENT_PLAN_MIN_BODY_LENGTH,
) -> MarketingContentPlanDraftQuality:
    """Score content plan structure without LLM — not a substitute for human review."""
    normalized = (body or "").strip()
    body_lower = normalized.lower()

    flags: dict[str, bool] = {}
    missing: list[str] = []
    for label, field_name, markers in _REQUIRED_SECTIONS:
        present = _section_present(body_lower, markers)
        flags[field_name] = present
        if not present:
            missing.append(label)

    min_body_length_met = len(normalized) >= min_length
    passed = sum(1 for _label, field_name, _markers in _REQUIRED_SECTIONS if flags[field_name])
    if min_body_length_met:
        passed += 1

    total_checks = len(_REQUIRED_SECTIONS) + 1
    score = round(passed / total_checks, 2) if total_checks else 0.0

    return MarketingContentPlanDraftQuality(
        has_content_plan_summary=flags["has_content_plan_summary"],
        has_funnel_gaps_to_cover=flags["has_funnel_gaps_to_cover"],
        has_recommended_assets_by_step=flags["has_recommended_assets_by_step"],
        has_priority_order=flags["has_priority_order"],
        has_production_notes=flags["has_production_notes"],
        has_risks_assumptions=flags["has_risks_assumptions"],
        min_body_length_met=min_body_length_met,
        score=score,
        missing_sections=missing,
    )


def is_content_plan_candidate(metadata: dict[str, Any] | None) -> bool:
    meta = metadata or {}
    return meta.get("purpose") == CONTENT_PLAN_PURPOSE


def enrich_content_plan_metadata(
    metadata: dict[str, Any] | None,
    body: str,
) -> dict[str, Any]:
    enriched = dict(metadata or {})
    quality = evaluate_content_plan_body(body)
    enriched["quality"] = quality.model_dump()
    return enriched


def build_mock_content_plan_body(*, goal: str = "") -> str:
    goal_line = goal or "Plan content production for the launch funnel."
    padding = (
        "This content plan draft maps gap analysis to concrete assets per funnel step. "
        "Humans assign assets to steps and approve drafts — the agent proposes only, "
        "it does not link assets or mutate funnel structure."
    )
    sections = "\n\n".join(
        f"## {label}\n{label} for {goal_line}"
        for label, _field, _markers in _REQUIRED_SECTIONS
    )
    body = f"{sections}\n\n{padding}"
    assert len(body) >= DEFAULT_CONTENT_PLAN_MIN_BODY_LENGTH
    return body


def default_content_planner_draft_metadata(
    *,
    funnel_id: str | None = None,
    goal: str = "",
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "purpose": CONTENT_PLAN_PURPOSE,
        "source": "content_planner_agent",
    }
    if funnel_id:
        meta["funnel_id"] = funnel_id
    if goal:
        meta["goal"] = goal
    return meta
