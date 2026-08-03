"""Phase 5.2 — copy draft quality contract."""

from __future__ import annotations

from app.marketing.contracts import ContentAssetType
from app.marketing.copy_quality import (
    build_mock_copy_draft_body,
    evaluate_copy_draft_body,
)


def test_email_complete_body_scores_high() -> None:
    body = build_mock_copy_draft_body(ContentAssetType.EMAIL, goal="Launch campaign")
    quality = evaluate_copy_draft_body(ContentAssetType.EMAIL, body)
    assert quality.has_subject_line is True
    assert quality.has_preview_text is True
    assert quality.has_body is True
    assert quality.has_cta is True
    assert quality.min_body_length_met is True
    assert quality.missing_sections == []
    assert quality.score == 1.0


def test_email_missing_cta_lowers_score() -> None:
    body = (
        "Subject line: Hello\n\n"
        "Preview text: Short preview\n\n"
        "Body:\nSome content here for the reader."
    )
    quality = evaluate_copy_draft_body(ContentAssetType.EMAIL, body)
    assert quality.has_cta is False
    assert "CTA" in quality.missing_sections
    assert quality.score < 1.0


def test_ad_copy_sections_checked() -> None:
    body = build_mock_copy_draft_body(ContentAssetType.AD_COPY)
    quality = evaluate_copy_draft_body(ContentAssetType.AD_COPY, body)
    assert quality.has_hook is True
    assert quality.has_offer is True
    assert quality.has_proof is True
    assert quality.has_cta is True
    assert quality.score == 1.0


def test_telegram_sections_checked() -> None:
    body = build_mock_copy_draft_body(ContentAssetType.TELEGRAM_POST)
    quality = evaluate_copy_draft_body(ContentAssetType.TELEGRAM_POST, body)
    assert quality.has_hook is True
    assert quality.has_value is True
    assert quality.has_cta is True
    assert quality.score == 1.0
