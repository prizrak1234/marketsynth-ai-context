"""Content review draft quality contract (Phase 5.4) — deterministic heuristics only."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

DEFAULT_REVIEW_MIN_BODY_LENGTH = 400

CONTENT_REVIEW_PURPOSE = "content_review"

_REQUIRED_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Verdict", "has_verdict", ("## verdict", "\nverdict\n", "verdict:")),
    ("Strengths", "has_strengths", ("## strengths", "\nstrengths\n", "strengths:")),
    ("Issues", "has_issues", ("## issues", "\nissues\n", "issues:")),
    (
        "Suggested fixes",
        "has_suggested_fixes",
        ("## suggested fixes", "suggested fixes"),
    ),
    ("Risks", "has_risks", ("## risks", "\nrisks\n", "risks:")),
    (
        "Approval recommendation",
        "has_approval_recommendation",
        (
            "## approval recommendation",
            "approval recommendation",
        ),
    ),
)


class MarketingContentReviewDraftQuality(BaseModel):
    has_verdict: bool = False
    has_strengths: bool = False
    has_issues: bool = False
    has_suggested_fixes: bool = False
    has_risks: bool = False
    has_approval_recommendation: bool = False
    min_body_length_met: bool = False
    score: float = 0.0
    missing_sections: list[str] = Field(default_factory=list)


def _section_present(body_lower: str, markers: tuple[str, ...]) -> bool:
    return any(marker in body_lower for marker in markers)


def evaluate_review_body(
    body: str,
    *,
    min_length: int = DEFAULT_REVIEW_MIN_BODY_LENGTH,
) -> MarketingContentReviewDraftQuality:
    """Score review draft structure without LLM — not a substitute for human review."""
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

    return MarketingContentReviewDraftQuality(
        has_verdict=flags["has_verdict"],
        has_strengths=flags["has_strengths"],
        has_issues=flags["has_issues"],
        has_suggested_fixes=flags["has_suggested_fixes"],
        has_risks=flags["has_risks"],
        has_approval_recommendation=flags["has_approval_recommendation"],
        min_body_length_met=min_body_length_met,
        score=score,
        missing_sections=missing,
    )


def is_content_review_candidate(metadata: dict[str, Any] | None) -> bool:
    meta = metadata or {}
    return meta.get("purpose") == CONTENT_REVIEW_PURPOSE


def enrich_content_review_metadata(
    metadata: dict[str, Any] | None,
    body: str,
) -> dict[str, Any]:
    enriched = dict(metadata or {})
    quality = evaluate_review_body(body)
    enriched["quality"] = quality.model_dump()
    return enriched


def build_mock_review_body(*, goal: str = "") -> str:
    goal_line = goal or "Review the source asset before human approval."
    padding = (
        "This review draft records findings only — it does not edit, approve, or publish "
        "the source content asset. Human marketers remain responsible for approval. "
        "Expand each section with brief-specific observations before sign-off; the quality "
        "score is a heuristic checklist only, not an automatic approval gate."
    )
    sections = "\n\n".join(
        f"## {label}\n{label} for: {goal_line}"
        for label, _field, _markers in _REQUIRED_SECTIONS
    )
    body = f"{sections}\n\n{padding}"
    assert len(body) >= DEFAULT_REVIEW_MIN_BODY_LENGTH
    return body


def default_critic_draft_metadata(
    *,
    source_asset_id: str | None = None,
    goal: str = "",
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "purpose": CONTENT_REVIEW_PURPOSE,
        "source": "critic_agent",
    }
    if source_asset_id:
        meta["source_asset_id"] = source_asset_id
    if goal:
        meta["goal"] = goal
    return meta
