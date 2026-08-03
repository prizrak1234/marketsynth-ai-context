"""Marketing strategy draft quality contract (Phase 5.1) — deterministic heuristics only."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.marketing.contracts import ContentAssetType

DEFAULT_STRATEGY_MIN_BODY_LENGTH = 500

STRATEGY_DRAFT_PURPOSE = "marketing_strategy"

_REQUIRED_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Summary", "has_summary", ("## summary", "# summary")),
    ("Funnel gaps", "has_funnel_gaps", ("## funnel gaps", "funnel gaps")),
    (
        "Recommended assets",
        "has_recommended_assets",
        ("## recommended assets", "recommended assets"),
    ),
    ("Next actions", "has_next_actions", ("## next actions", "next actions")),
    ("Risks", "has_risks", ("## risks", "# risks", "\nrisks\n")),
)


class MarketingStrategyDraftQuality(BaseModel):
    has_summary: bool = False
    has_funnel_gaps: bool = False
    has_recommended_assets: bool = False
    has_next_actions: bool = False
    has_risks: bool = False
    min_body_length_met: bool = False
    score: float = 0.0
    missing_sections: list[str] = Field(default_factory=list)


def _section_present(body_lower: str, markers: tuple[str, ...]) -> bool:
    return any(marker in body_lower for marker in markers)


def evaluate_strategy_draft_body(
    body: str,
    *,
    min_length: int = DEFAULT_STRATEGY_MIN_BODY_LENGTH,
) -> MarketingStrategyDraftQuality:
    """Score strategy draft structure without LLM — not a substitute for human review."""
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

    return MarketingStrategyDraftQuality(
        has_summary=flags["has_summary"],
        has_funnel_gaps=flags["has_funnel_gaps"],
        has_recommended_assets=flags["has_recommended_assets"],
        has_next_actions=flags["has_next_actions"],
        has_risks=flags["has_risks"],
        min_body_length_met=min_body_length_met,
        score=score,
        missing_sections=missing,
    )


def is_strategy_draft_candidate(
    asset_type: ContentAssetType,
    title: str,
    metadata: dict[str, Any] | None,
) -> bool:
    if asset_type != ContentAssetType.ARTICLE:
        return False
    meta = metadata or {}
    if meta.get("purpose") == STRATEGY_DRAFT_PURPOSE:
        return True
    return "strategy" in (title or "").lower()


def enrich_strategy_draft_metadata(
    metadata: dict[str, Any] | None,
    body: str,
) -> dict[str, Any]:
    enriched = dict(metadata or {})
    quality = evaluate_strategy_draft_body(body)
    enriched["quality"] = quality.model_dump()
    return enriched


def resolve_strategy_draft_quality(
    *,
    body: str,
    metadata: dict[str, Any] | None,
) -> MarketingStrategyDraftQuality:
    meta = metadata or {}
    stored = meta.get("quality")
    if isinstance(stored, dict):
        return MarketingStrategyDraftQuality.model_validate(stored)
    return evaluate_strategy_draft_body(body)


def build_mock_strategy_draft_body() -> str:
    """Deterministic mock body for strategist flows (all sections, min length)."""
    padding = (
        "This strategy draft expands on gap analysis findings and ties recommendations "
        "to the current funnel. Each section should be reviewed by a human marketer "
        "before approval — the quality score is a heuristic only, not sign-off."
    )
    sections = "\n\n".join(
        f"## {label}\n{label} content for smoke and mock strategist runs."
        for label, _field, _markers in _REQUIRED_SECTIONS
    )
    body = f"{sections}\n\n{padding}"
    assert len(body) >= DEFAULT_STRATEGY_MIN_BODY_LENGTH
    return body


def default_strategist_draft_metadata() -> dict[str, Any]:
    return {
        "purpose": STRATEGY_DRAFT_PURPOSE,
        "source": "strategist_agent",
    }
