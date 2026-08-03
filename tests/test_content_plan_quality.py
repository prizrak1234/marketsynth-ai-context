"""Phase 5.3 — content plan draft quality contract."""

from __future__ import annotations

from app.marketing.content_plan_quality import (
    DEFAULT_CONTENT_PLAN_MIN_BODY_LENGTH,
    build_mock_content_plan_body,
    evaluate_content_plan_body,
)


def test_complete_content_plan_scores_high() -> None:
    body = build_mock_content_plan_body(goal="Launch funnel")
    quality = evaluate_content_plan_body(body)
    assert quality.has_content_plan_summary is True
    assert quality.has_funnel_gaps_to_cover is True
    assert quality.has_recommended_assets_by_step is True
    assert quality.has_priority_order is True
    assert quality.has_production_notes is True
    assert quality.has_risks_assumptions is True
    assert quality.min_body_length_met is True
    assert quality.missing_sections == []
    assert quality.score == 1.0


def test_missing_priority_lowers_score() -> None:
    body = (
        "## Content plan summary\nSummary\n\n"
        "## Funnel gaps to cover\nGaps\n\n"
        "## Recommended assets by funnel step\nAssets\n\n"
        "## Production notes\nNotes\n\n"
        "## Risks / assumptions\nRisks"
    )
    quality = evaluate_content_plan_body(body)
    assert quality.has_priority_order is False
    assert "Priority order" in quality.missing_sections
    assert quality.score < 1.0


def test_min_length_enforced() -> None:
    short_body = (
        "## Content plan summary\nx\n\n"
        "## Funnel gaps to cover\nx\n\n"
        "## Recommended assets by funnel step\nx\n\n"
        "## Priority order\nx\n\n"
        "## Production notes\nx\n\n"
        "## Risks / assumptions\nx"
    )
    quality = evaluate_content_plan_body(
        short_body,
        min_length=DEFAULT_CONTENT_PLAN_MIN_BODY_LENGTH,
    )
    assert quality.min_body_length_met is False
    assert quality.score < 1.0
