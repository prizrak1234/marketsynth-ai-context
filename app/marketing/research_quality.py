"""Research draft quality contract (Phase 5.5) — deterministic heuristics only."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

DEFAULT_RESEARCH_MIN_BODY_LENGTH = 500

RESEARCH_DRAFT_PURPOSE = "research_draft"

_REQUIRED_SECTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Research summary",
        "has_research_summary",
        ("## research summary", "research summary"),
    ),
    (
        "Known project facts",
        "has_known_project_facts",
        ("## known project facts", "known project facts"),
    ),
    (
        "Audience / market assumptions",
        "has_audience_market_assumptions",
        (
            "## audience / market assumptions",
            "audience / market assumptions",
            "audience assumptions",
            "market assumptions",
        ),
    ),
    (
        "Competitive angles to validate",
        "has_competitive_angles",
        (
            "## competitive angles to validate",
            "competitive angles to validate",
        ),
    ),
    (
        "Content opportunities",
        "has_content_opportunities",
        ("## content opportunities", "content opportunities"),
    ),
    (
        "Open questions",
        "has_open_questions",
        ("## open questions", "open questions"),
    ),
    (
        "Risks / external validation needed",
        "has_external_validation_section",
        (
            "## risks / external validation needed",
            "risks / external validation needed",
            "requires external validation",
            "external validation needed",
        ),
    ),
)


class MarketingResearchDraftQuality(BaseModel):
    has_research_summary: bool = False
    has_known_project_facts: bool = False
    has_audience_market_assumptions: bool = False
    has_competitive_angles: bool = False
    has_content_opportunities: bool = False
    has_open_questions: bool = False
    has_external_validation_section: bool = False
    min_body_length_met: bool = False
    score: float = 0.0
    missing_sections: list[str] = Field(default_factory=list)


def _section_present(body_lower: str, markers: tuple[str, ...]) -> bool:
    return any(marker in body_lower for marker in markers)


def evaluate_research_body(
    body: str,
    *,
    min_length: int = DEFAULT_RESEARCH_MIN_BODY_LENGTH,
) -> MarketingResearchDraftQuality:
    """Score research draft structure without LLM — not a substitute for human review."""
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

    return MarketingResearchDraftQuality(
        has_research_summary=flags["has_research_summary"],
        has_known_project_facts=flags["has_known_project_facts"],
        has_audience_market_assumptions=flags["has_audience_market_assumptions"],
        has_competitive_angles=flags["has_competitive_angles"],
        has_content_opportunities=flags["has_content_opportunities"],
        has_open_questions=flags["has_open_questions"],
        has_external_validation_section=flags["has_external_validation_section"],
        min_body_length_met=min_body_length_met,
        score=score,
        missing_sections=missing,
    )


def is_research_draft_candidate(metadata: dict[str, Any] | None) -> bool:
    meta = metadata or {}
    return meta.get("purpose") == RESEARCH_DRAFT_PURPOSE


def enrich_research_draft_metadata(
    metadata: dict[str, Any] | None,
    body: str,
) -> dict[str, Any]:
    enriched = dict(metadata or {})
    quality = evaluate_research_body(body)
    enriched["quality"] = quality.model_dump()
    return enriched


def build_mock_research_body(*, goal: str = "", research_topic: str = "") -> str:
    topic_line = research_topic or "internal project research"
    goal_line = goal or "prepare internal research memo"
    padding = (
        "This research draft uses only in-project tools — no web search or external citations. "
        "Label assumptions explicitly; anything not grounded in tool results requires external "
        "validation before treating it as verified market fact."
    )
    sections = "\n\n".join(
        f"## {label}\n{label} for topic '{topic_line}' — {goal_line}. "
        "Requires external validation for claims beyond project data."
        for label, _field, _markers in _REQUIRED_SECTIONS
    )
    body = f"{sections}\n\n{padding}"
    assert len(body) >= DEFAULT_RESEARCH_MIN_BODY_LENGTH
    return body


def default_researcher_draft_metadata(
    *,
    research_topic: str = "",
    goal: str = "",
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "purpose": RESEARCH_DRAFT_PURPOSE,
        "source": "researcher_agent",
    }
    if research_topic:
        meta["research_topic"] = research_topic
    if goal:
        meta["goal"] = goal
    return meta
