"""Phase 5.4 — content review draft quality contract."""

from __future__ import annotations

from app.marketing.review_quality import (
    DEFAULT_REVIEW_MIN_BODY_LENGTH,
    build_mock_review_body,
    evaluate_review_body,
)


def test_complete_review_body_scores_high() -> None:
    body = build_mock_review_body(goal="Pre-approval review")
    quality = evaluate_review_body(body)
    assert quality.has_verdict is True
    assert quality.has_strengths is True
    assert quality.has_issues is True
    assert quality.has_suggested_fixes is True
    assert quality.has_risks is True
    assert quality.has_approval_recommendation is True
    assert quality.min_body_length_met is True
    assert quality.missing_sections == []
    assert quality.score == 1.0


def test_missing_verdict_lowers_score() -> None:
    body = (
        "## Strengths\nGood hook\n\n"
        "## Issues\nWeak CTA\n\n"
        "## Suggested fixes\nTighten CTA\n\n"
        "## Risks\nCompliance\n\n"
        "## Approval recommendation\nRevise first"
    )
    quality = evaluate_review_body(body)
    assert quality.has_verdict is False
    assert "Verdict" in quality.missing_sections
    assert quality.score < 1.0


def test_min_length_enforced() -> None:
    short_body = (
        "## Verdict\nok\n\n## Strengths\nx\n\n## Issues\nx\n\n"
        "## Suggested fixes\nx\n\n## Risks\nx\n\n## Approval recommendation\nx"
    )
    quality = evaluate_review_body(
        short_body,
        min_length=DEFAULT_REVIEW_MIN_BODY_LENGTH,
    )
    assert quality.min_body_length_met is False
    assert quality.score < 1.0
