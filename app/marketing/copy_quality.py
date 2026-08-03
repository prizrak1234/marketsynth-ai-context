"""Copy draft quality contract (Phase 5.2) — deterministic heuristics only."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.marketing.contracts import ContentAssetType

COPY_DRAFT_PURPOSE = "copy_draft"

DEFAULT_COPY_MIN_BODY_LENGTH = 120

_EMAIL_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Subject line", "has_subject_line", ("subject line", "subject:")),
    ("Preview text", "has_preview_text", ("preview text", "preview:")),
    ("Body", "has_body", ("## body", "\nbody\n", "body:")),
    ("CTA", "has_cta", ("cta", "call to action", "call-to-action")),
)

_AD_COPY_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Hook", "has_hook", ("## hook", "\nhook\n", "hook:")),
    ("Offer", "has_offer", ("## offer", "\noffer\n", "offer:")),
    ("Proof", "has_proof", ("## proof", "\nproof\n", "proof:")),
    ("CTA", "has_cta", ("cta", "call to action", "call-to-action")),
)

_TELEGRAM_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Hook", "has_hook", ("## hook", "\nhook\n", "hook:")),
    ("Value", "has_value", ("## value", "\nvalue\n", "value:")),
    ("CTA", "has_cta", ("cta", "call to action", "call-to-action")),
)

_SECTIONS_BY_TYPE: dict[ContentAssetType, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    ContentAssetType.EMAIL: _EMAIL_SECTIONS,
    ContentAssetType.AD_COPY: _AD_COPY_SECTIONS,
    ContentAssetType.TELEGRAM_POST: _TELEGRAM_SECTIONS,
}


class MarketingCopyDraftQuality(BaseModel):
    asset_type: str
    has_subject_line: bool = False
    has_preview_text: bool = False
    has_body: bool = False
    has_hook: bool = False
    has_offer: bool = False
    has_proof: bool = False
    has_value: bool = False
    has_cta: bool = False
    min_body_length_met: bool = False
    score: float = 0.0
    missing_sections: list[str] = Field(default_factory=list)


def _section_present(body_lower: str, markers: tuple[str, ...]) -> bool:
    return any(marker in body_lower for marker in markers)


def _sections_for_type(
    asset_type: ContentAssetType,
) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    return _SECTIONS_BY_TYPE.get(asset_type, _EMAIL_SECTIONS)


def evaluate_copy_draft_body(
    asset_type: ContentAssetType | str,
    body: str,
    *,
    min_length: int = DEFAULT_COPY_MIN_BODY_LENGTH,
) -> MarketingCopyDraftQuality:
    """Score copy draft structure without LLM — not a substitute for human review."""
    if isinstance(asset_type, str):
        asset_type = ContentAssetType(asset_type.strip().lower())

    normalized = (body or "").strip()
    body_lower = normalized.lower()
    sections = _sections_for_type(asset_type)

    flags: dict[str, bool] = {}
    missing: list[str] = []
    for label, field_name, markers in sections:
        present = _section_present(body_lower, markers)
        flags[field_name] = present
        if not present:
            missing.append(label)

    min_body_length_met = len(normalized) >= min_length
    passed = sum(1 for _label, field_name, _markers in sections if flags[field_name])
    if min_body_length_met:
        passed += 1

    total_checks = len(sections) + 1
    score = round(passed / total_checks, 2) if total_checks else 0.0

    return MarketingCopyDraftQuality(
        asset_type=asset_type.value,
        has_subject_line=flags.get("has_subject_line", False),
        has_preview_text=flags.get("has_preview_text", False),
        has_body=flags.get("has_body", False),
        has_hook=flags.get("has_hook", False),
        has_offer=flags.get("has_offer", False),
        has_proof=flags.get("has_proof", False),
        has_value=flags.get("has_value", False),
        has_cta=flags.get("has_cta", False),
        min_body_length_met=min_body_length_met,
        score=score,
        missing_sections=missing,
    )


def is_copy_draft_candidate(metadata: dict[str, Any] | None) -> bool:
    meta = metadata or {}
    return meta.get("purpose") == COPY_DRAFT_PURPOSE


def enrich_copy_draft_metadata(
    metadata: dict[str, Any] | None,
    *,
    asset_type: ContentAssetType,
    body: str,
) -> dict[str, Any]:
    enriched = dict(metadata or {})
    quality = evaluate_copy_draft_body(asset_type, body)
    enriched["quality"] = quality.model_dump()
    return enriched


def build_mock_copy_draft_body(asset_type: ContentAssetType | str, *, goal: str = "") -> str:
    if isinstance(asset_type, str):
        asset_type = ContentAssetType(asset_type.strip().lower())

    goal_line = goal or "Drive conversions for the current campaign."
    if asset_type == ContentAssetType.EMAIL:
        return (
            f"Subject line: Launch update for your audience\n\n"
            f"Preview text: A concise preview aligned with the brief.\n\n"
            f"Body:\n{goal_line}\n"
            "This email introduces the offer, reinforces trust, and guides the reader "
            "toward a single next step. Expand with proof points from linked assets.\n\n"
            f"CTA: Start your free trial today"
        )
    if asset_type == ContentAssetType.AD_COPY:
        return (
            f"Hook: Stop scrolling — your next customer is one click away.\n\n"
            f"Offer: {goal_line}\n\n"
            "Proof: Social proof and product outcomes sourced from brief and funnel assets.\n\n"
            "CTA: Get started now"
        )
    if asset_type == ContentAssetType.TELEGRAM_POST:
        return (
            f"Hook: Quick win for founders building funnels.\n\n"
            f"Value: {goal_line}\n\n"
            "CTA: Reply with FUNNEL for the checklist"
        )
    return (
        f"Hook: {goal_line}\n\n"
        "Offer: Core value proposition from the brief.\n\n"
        "Proof: Customer outcomes and credibility markers.\n\n"
        "CTA: Learn more"
    )


def default_copywriter_draft_metadata(*, goal: str = "") -> dict[str, Any]:
    meta: dict[str, Any] = {
        "purpose": COPY_DRAFT_PURPOSE,
        "source": "copywriter_agent",
    }
    if goal:
        meta["goal"] = goal
    return meta
