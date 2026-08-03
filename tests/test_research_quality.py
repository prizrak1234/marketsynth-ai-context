"""Phase 5.5 — research draft quality contract."""

from __future__ import annotations

from app.marketing.research_quality import (
    DEFAULT_RESEARCH_MIN_BODY_LENGTH,
    build_mock_research_body,
    evaluate_research_body,
)


def test_complete_research_draft_scores_high() -> None:
    body = build_mock_research_body(
        goal="prepare internal research memo",
        research_topic="audience objections",
    )
    quality = evaluate_research_body(body)
    assert quality.has_research_summary is True
    assert quality.has_known_project_facts is True
    assert quality.has_audience_market_assumptions is True
    assert quality.has_competitive_angles is True
    assert quality.has_content_opportunities is True
    assert quality.has_open_questions is True
    assert quality.has_external_validation_section is True
    assert quality.min_body_length_met is True
    assert quality.missing_sections == []
    assert quality.score == 1.0


def test_missing_external_validation_section_lowers_score() -> None:
    body = (
        "## Research summary\nSummary\n\n"
        "## Known project facts\nFacts\n\n"
        "## Audience / market assumptions\nAssumptions\n\n"
        "## Competitive angles to validate\nAngles\n\n"
        "## Content opportunities\nOps\n\n"
        "## Open questions\nQuestions"
    )
    quality = evaluate_research_body(body)
    assert quality.has_external_validation_section is False
    assert "Risks / external validation needed" in quality.missing_sections
    assert quality.score < 1.0


def test_min_length_enforced() -> None:
    short_body = (
        "## Research summary\nx\n\n## Known project facts\nx\n\n"
        "## Audience / market assumptions\nx\n\n"
        "## Competitive angles to validate\nx\n\n"
        "## Content opportunities\nx\n\n"
        "## Open questions\nx\n\n"
        "## Risks / external validation needed\nx"
    )
    quality = evaluate_research_body(
        short_body,
        min_length=DEFAULT_RESEARCH_MIN_BODY_LENGTH,
    )
    assert quality.min_body_length_met is False
    assert quality.score < 1.0
