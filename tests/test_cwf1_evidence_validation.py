"""Tests for CWF.1 evidence validation."""

from __future__ import annotations

from app.business_idea_validation.evidence_validation import (
    clean_excerpt_for_finding,
    is_boilerplate_content,
    is_valid_source_url,
    validate_evidence_acceptance,
)

SAMPLE_NAV_BLOB = (
    "[Смотреть рейтинг]() [Аналитика рынка 2025 года]() "
    "81 компаний в основном рейтинге CRM и продажи HR платформа "
    "Автоматизация HoReCa Автоматизация бизнес-процессов"
)


def test_rejects_empty_markdown_links_as_boilerplate() -> None:
    assert is_boilerplate_content(SAMPLE_NAV_BLOB) is True


def test_rejects_missing_url() -> None:
    accepted, reason = validate_evidence_acceptance(
        observation="Рынок SaaS растёт двузначными темпами в сегменте SMB.",
        source_url=None,
    )
    assert accepted is False
    assert reason == "missing_url"


def test_rejects_navigation_excerpt() -> None:
    accepted, reason = validate_evidence_acceptance(
        observation=SAMPLE_NAV_BLOB,
        source_url="https://example.com/report",
        source_title="Example Report",
    )
    assert accepted is False
    assert reason in {"empty_or_navigation_excerpt", "boilerplate_content", "empty_markdown_link"}


def test_accepts_clean_claim_with_url() -> None:
    claim = (
        "Спрос на онлайн-обучение для взрослых в Telegram сохраняется "
        "на уровне двузначного роста по данным отраслевого обзора."
    )
    accepted, reason = validate_evidence_acceptance(
        observation=claim,
        source_url="https://example.com/edtech-2025",
        source_title="EdTech Outlook 2025",
    )
    assert accepted is True
    assert reason is None
    cleaned = clean_excerpt_for_finding(claim)
    assert "example.com" not in cleaned
    assert len(cleaned) >= 24


def test_is_valid_source_url() -> None:
    assert is_valid_source_url("https://marketsynth.example/report") is True
    assert is_valid_source_url("") is False
    assert is_valid_source_url("ftp://bad") is False
