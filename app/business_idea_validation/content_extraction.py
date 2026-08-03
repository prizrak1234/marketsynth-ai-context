"""Content extraction and normalization — fetch success requires clean main text."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from app.business_idea_validation.sanitization import sanitize_source_body

_MIN_CLEAN_LENGTH = 80
_SUPPORTED_LANGS = frozenset({"ru", "en", "uk", "de", "fr", "es", "unknown"})

_STRIP_BLOCKS = re.compile(
    r"<(script|style|nav|header|footer|aside|noscript|iframe)[^>]*>.*?</\1>",
    re.I | re.S,
)
_TAG = re.compile(r"<[^>]+>")
_TITLE = re.compile(r"<title[^>]*>([^<]+)</title>", re.I | re.S)
_META_PUBLISHER = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:author|og:site_name|publisher)["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_META_DATE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:article:published_time|date|pubdate)["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)

_NAV_MARKERS = (
    "skip to content",
    "skip to main",
    "cookie policy",
    "accept all cookies",
    "privacy policy",
    "terms of service",
    "sign in",
    "log in",
    "menu",
    "navigation",
    "breadcrumb",
    "перейти к содержанию",
    "принять все cookie",
    "политика конфиденциальности",
)

_JS_SHELL = re.compile(
    r"(enable javascript|javascript is disabled|requires javascript|"
    r"checking your browser|cloudflare|just a moment|"
    r"document\.getelementbyid|<noscript)",
    re.I,
)

_SEARCH_PAGE = re.compile(
    r"(search results for|results found|ничего не найдено|результаты поиска|"
    r"showing \d+ results|найдено \d+)",
    re.I,
)

_CATEGORY_LISTING = re.compile(
    r"(category:|categories|категори[ия]|browse all|все товары|catalog)",
    re.I,
)

_BOILERPLATE_LINES = frozenset(
    {
        "home",
        "about us",
        "contact",
        "subscribe",
        "newsletter",
        "follow us",
        "all rights reserved",
        "главная",
        "контакты",
        "подписаться",
    }
)


class ExtractionRejectionReason(StrEnum):
    EMPTY_CONTENT = "empty_content"
    CONTENT_TOO_SHORT = "content_too_short"
    NAVIGATION_ONLY = "navigation_only"
    BOILERPLATE_DOMINANT = "boilerplate_dominant"
    DUPLICATE_DOCUMENT = "duplicate_document"
    MALFORMED_CONTENT = "malformed_content"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    NO_MAIN_CONTENT = "no_main_content"
    SEARCH_RESULTS_PAGE = "search_results_page"
    CATEGORY_PAGE_WITHOUT_CLAIMS = "category_page_without_claims"
    JAVASCRIPT_SHELL = "javascript_shell"


class ExtractionStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(slots=True)
class ContentExtractionResult:
    document_id: UUID
    extraction_status: ExtractionStatus
    rejection_reason: ExtractionRejectionReason | None = None
    title: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    language: str = "unknown"
    region: str | None = None
    content_type: str = "text/plain"
    raw_length: int = 0
    clean_length: int = 0
    clean_text: str = ""
    content_fingerprint: str = ""
    quality_score: float = 0.0
    metadata_complete: bool = False


@dataclass
class ExtractionRunContext:
    """Per-run deduplication registry for normalized documents."""

    seen_fingerprints: set[str] = field(default_factory=set)


def detect_content_type(raw: str, header_content_type: str | None) -> str:
    ct = (header_content_type or "").split(";")[0].strip().lower()
    if ct:
        return ct
    sample = (raw or "")[:500].lower()
    if sample.lstrip().startswith("<!doctype") or "<html" in sample:
        return "text/html"
    if sample.lstrip().startswith("{") or sample.lstrip().startswith("["):
        return "application/json"
    return "text/plain"


def strip_html_boilerplate(html: str) -> str:
    text = _STRIP_BLOCKS.sub(" ", html or "")
    text = _TAG.sub(" ", text)
    return sanitize_source_body(text)


def remove_duplicate_blocks(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        key = line.lower()
        if len(key) < 24:
            unique.append(line)
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(line)
    return "\n".join(unique)


def extract_metadata(raw: str, *, title_hint: str | None = None) -> tuple[str | None, str | None, str | None]:
    title = title_hint
    if not title:
        match = _TITLE.search(raw or "")
        title = match.group(1).strip()[:300] if match else None
    publisher_match = _META_PUBLISHER.search(raw or "")
    publisher = publisher_match.group(1).strip()[:255] if publisher_match else None
    date_match = _META_DATE.search(raw or "")
    published_at = date_match.group(1).strip()[:64] if date_match else None
    return title, publisher, published_at


def detect_language(text: str) -> str:
    sample = (text or "")[:2000].lower()
    cyr = sum(1 for ch in sample if "\u0400" <= ch <= "\u04ff")
    lat = sum(1 for ch in sample if "a" <= ch <= "z")
    if cyr > lat and cyr > 20:
        return "ru"
    if lat > 20:
        return "en"
    return "unknown"


def compute_content_fingerprint(text: str) -> str:
    normalized = " ".join((text or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()[:32]


def _boilerplate_ratio(lines: list[str]) -> float:
    if not lines:
        return 1.0
    boiler = sum(1 for ln in lines if ln.lower() in _BOILERPLATE_LINES or len(ln) < 4)
    return boiler / len(lines)


def _navigation_score(text: str) -> float:
    lower = text.lower()
    hits = sum(1 for m in _NAV_MARKERS if m in lower)
    return hits / max(len(_NAV_MARKERS), 1)


def compute_quality_score(*, clean_text: str, title: str | None, metadata_complete: bool) -> float:
    score = min(1.0, len(clean_text) / 1200)
    if title:
        score += 0.15
    if metadata_complete:
        score += 0.1
    if _navigation_score(clean_text) > 0.25:
        score -= 0.35
    return max(0.0, min(1.0, score))


def validate_clean_content(
    clean_text: str,
    *,
    raw: str,
    content_type: str,
) -> ExtractionRejectionReason | None:
    if _JS_SHELL.search(raw[:4000]) and len(clean_text.strip()) < 400:
        return ExtractionRejectionReason.JAVASCRIPT_SHELL
    if not clean_text.strip():
        return ExtractionRejectionReason.EMPTY_CONTENT
    if _SEARCH_PAGE.search(clean_text[:1500]):
        return ExtractionRejectionReason.SEARCH_RESULTS_PAGE
    if len(clean_text.strip()) < _MIN_CLEAN_LENGTH:
        return ExtractionRejectionReason.CONTENT_TOO_SHORT
    lines = [ln.strip() for ln in clean_text.splitlines() if ln.strip()]
    if _boilerplate_ratio(lines) > 0.55:
        return ExtractionRejectionReason.BOILERPLATE_DOMINANT
    if _navigation_score(clean_text) > 0.35 and len(clean_text) < 600:
        return ExtractionRejectionReason.NAVIGATION_ONLY
    if _SEARCH_PAGE.search(clean_text[:1500]):
        return ExtractionRejectionReason.SEARCH_RESULTS_PAGE
    if _CATEGORY_LISTING.search(clean_text[:800]) and len(clean_text) < 500:
        return ExtractionRejectionReason.CATEGORY_PAGE_WITHOUT_CLAIMS
    if content_type.startswith("application/pdf") or "octet-stream" in content_type:
        return ExtractionRejectionReason.MALFORMED_CONTENT
    lang = detect_language(clean_text)
    if lang not in _SUPPORTED_LANGS:
        return ExtractionRejectionReason.UNSUPPORTED_LANGUAGE
    substantive = [ln for ln in lines if len(ln) >= 40]
    if not substantive:
        return ExtractionRejectionReason.NO_MAIN_CONTENT
    return None


def rejection_to_fetch_outcome(reason: ExtractionRejectionReason):
    from app.schemas.contracts import BivFetchOutcomeCode

    mapping = {
        ExtractionRejectionReason.EMPTY_CONTENT: BivFetchOutcomeCode.EMPTY_CONTENT,
        ExtractionRejectionReason.CONTENT_TOO_SHORT: BivFetchOutcomeCode.CONTENT_TOO_SHORT,
        ExtractionRejectionReason.NAVIGATION_ONLY: BivFetchOutcomeCode.EMPTY_CONTENT,
        ExtractionRejectionReason.BOILERPLATE_DOMINANT: BivFetchOutcomeCode.EMPTY_CONTENT,
        ExtractionRejectionReason.DUPLICATE_DOCUMENT: BivFetchOutcomeCode.DUPLICATE_URL,
        ExtractionRejectionReason.MALFORMED_CONTENT: BivFetchOutcomeCode.MALFORMED_CONTENT,
        ExtractionRejectionReason.UNSUPPORTED_LANGUAGE: BivFetchOutcomeCode.UNSUPPORTED_CONTENT_TYPE,
        ExtractionRejectionReason.NO_MAIN_CONTENT: BivFetchOutcomeCode.EMPTY_CONTENT,
        ExtractionRejectionReason.SEARCH_RESULTS_PAGE: BivFetchOutcomeCode.EMPTY_CONTENT,
        ExtractionRejectionReason.CATEGORY_PAGE_WITHOUT_CLAIMS: BivFetchOutcomeCode.CONTENT_TOO_SHORT,
        ExtractionRejectionReason.JAVASCRIPT_SHELL: BivFetchOutcomeCode.JAVASCRIPT_REQUIRED,
    }
    return mapping[reason]


def extract_and_normalize_document(
    raw: str,
    *,
    source_url: str,
    header_content_type: str | None = None,
    title_hint: str | None = None,
    run_context: ExtractionRunContext | None = None,
    document_id: UUID | None = None,
) -> ContentExtractionResult:
    """Full extraction pipeline: raw response → normalized document or rejection."""
    doc_id = document_id or uuid4()
    raw_len = len(raw or "")
    content_type = detect_content_type(raw, header_content_type)

    if content_type.startswith("application/pdf"):
        return ContentExtractionResult(
            document_id=doc_id,
            extraction_status=ExtractionStatus.REJECTED,
            rejection_reason=ExtractionRejectionReason.MALFORMED_CONTENT,
            content_type=content_type,
            raw_length=raw_len,
        )

    if content_type in {"text/html", "application/xhtml+xml"} or "<html" in (raw or "")[:300].lower():
        main_text = strip_html_boilerplate(raw)
    else:
        main_text = sanitize_source_body(raw)

    main_text = remove_duplicate_blocks(main_text)
    title, publisher, published_at = extract_metadata(raw, title_hint=title_hint)
    language = detect_language(main_text)
    region = "RU" if language == "ru" else None

    rejection = validate_clean_content(main_text, raw=raw, content_type=content_type)
    fingerprint = compute_content_fingerprint(main_text) if main_text else ""

    if rejection is None and run_context is not None and fingerprint:
        if fingerprint in run_context.seen_fingerprints:
            rejection = ExtractionRejectionReason.DUPLICATE_DOCUMENT
        else:
            run_context.seen_fingerprints.add(fingerprint)

    metadata_complete = bool(title and (publisher or published_at))
    quality = compute_quality_score(
        clean_text=main_text,
        title=title,
        metadata_complete=metadata_complete,
    )

    if rejection is not None:
        return ContentExtractionResult(
            document_id=doc_id,
            extraction_status=ExtractionStatus.REJECTED,
            rejection_reason=rejection,
            title=title,
            publisher=publisher,
            published_at=published_at,
            language=language,
            region=region,
            content_type=content_type,
            raw_length=raw_len,
            clean_length=len(main_text.strip()),
            clean_text=main_text,
            content_fingerprint=fingerprint,
            quality_score=quality,
            metadata_complete=metadata_complete,
        )

    return ContentExtractionResult(
        document_id=doc_id,
        extraction_status=ExtractionStatus.ACCEPTED,
        title=title,
        publisher=publisher,
        published_at=published_at,
        language=language,
        region=region,
        content_type=content_type,
        raw_length=raw_len,
        clean_length=len(main_text.strip()),
        clean_text=main_text,
        content_fingerprint=fingerprint,
        quality_score=quality,
        metadata_complete=metadata_complete,
    )
