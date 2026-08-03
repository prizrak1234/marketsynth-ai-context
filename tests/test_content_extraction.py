"""Content extraction hardening tests."""

from __future__ import annotations

from app.business_idea_validation.content_extraction import (
    ExtractionRejectionReason,
    ExtractionRunContext,
    ExtractionStatus,
    extract_and_normalize_document,
)


def test_rejects_empty_page() -> None:
    result = extract_and_normalize_document("", source_url="https://example.com/e")
    assert result.extraction_status == ExtractionStatus.REJECTED
    assert result.rejection_reason == ExtractionRejectionReason.EMPTY_CONTENT


def test_rejects_short_page() -> None:
    result = extract_and_normalize_document(
        "Short line without enough substantive content.",
        source_url="https://example.com/s",
    )
    assert result.rejection_reason in {
        ExtractionRejectionReason.CONTENT_TOO_SHORT,
        ExtractionRejectionReason.EMPTY_CONTENT,
        ExtractionRejectionReason.NO_MAIN_CONTENT,
    }


def test_rejects_js_shell() -> None:
    raw = "<html><body>Enable JavaScript to view this page.</body></html>"
    result = extract_and_normalize_document(raw, source_url="https://example.com/js")
    assert result.rejection_reason == ExtractionRejectionReason.JAVASCRIPT_SHELL


def test_rejects_navigation_menu_dom() -> None:
    raw = """
    <html><body>
    <nav>Home About Contact Subscribe Cookie Policy Skip to content</nav>
    <footer>All rights reserved Contact Subscribe</footer>
    </body></html>
    """
    result = extract_and_normalize_document(raw, source_url="https://example.com/nav")
    assert result.extraction_status == ExtractionStatus.REJECTED


def test_rejects_search_results_page() -> None:
    raw = "Search results for marketing automation. Showing 42 results found."
    result = extract_and_normalize_document(raw, source_url="https://example.com/search")
    assert result.rejection_reason == ExtractionRejectionReason.SEARCH_RESULTS_PAGE


def test_accepts_valid_article() -> None:
    body = (
        "The marketing automation market continues to expand as SMB teams adopt AI-assisted "
        "campaign workflows across Europe and North America. Analysts note sustained demand."
    )
    raw = f"<html><head><title>Market report</title></head><body><p>{body}</p></body></html>"
    result = extract_and_normalize_document(raw, source_url="https://example.com/article")
    assert result.extraction_status == ExtractionStatus.ACCEPTED
    assert result.clean_length >= 80
    assert result.content_fingerprint


def test_rejects_duplicate_content() -> None:
    ctx = ExtractionRunContext()
    text = "A" * 100 + " Valid article body about market demand and customer adoption trends."
    raw = f"<html><body><p>{text}</p></body></html>"
    first = extract_and_normalize_document(raw, source_url="https://a.com/1", run_context=ctx)
    second = extract_and_normalize_document(raw, source_url="https://b.com/2", run_context=ctx)
    assert first.extraction_status == ExtractionStatus.ACCEPTED
    assert second.rejection_reason == ExtractionRejectionReason.DUPLICATE_DOCUMENT


def test_strips_cookie_banner_and_footer() -> None:
    raw = """
    <html><body>
    <div>Accept all cookies and privacy policy banner text here removed.</div>
    <article>
    <p>Enterprise demand for AI marketing tools is rising among mid-market SaaS companies
    with repeatable onboarding and measurable retention outcomes across regions.</p>
    </article>
    <footer>Contact Subscribe Newsletter</footer>
    </body></html>
    """
    result = extract_and_normalize_document(raw, source_url="https://example.com/clean")
    assert result.extraction_status == ExtractionStatus.ACCEPTED
    assert "cookie" not in result.clean_text.lower()[:120]
