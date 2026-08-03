"""PRODUCT-01.3B — deterministic evidence text sanitization."""

from __future__ import annotations

import re
from urllib.parse import urlparse

_NAV_PATTERNS = (
    re.compile(r"\bto main content\b", re.I),
    re.compile(r"\bskip to (main|content|navigation)\b", re.I),
    re.compile(r"\b(cookie|privacy) policy\b", re.I),
    re.compile(r"\bsign in\b|\blog in\b|\bregister\b", re.I),
    re.compile(r"\bmenu\b|\bbreadcrumb\b|\bfooter\b|\bheader\b", re.I),
    re.compile(r"\bперейти к содержанию\b", re.I),
    re.compile(r"\bглавная\s*[›>]\s*", re.I),
)

_MARKDOWN_PATTERNS = (
    re.compile(r"\[[^\]]+\]\([^)]+\)"),
    re.compile(r"!\[[^\]]*\]\([^)]+\)"),
    re.compile(r"#{1,6}\s+"),
    re.compile(r"\*\*([^*]+)\*\*"),
    re.compile(r"__([^_]+)__"),
    re.compile(r"`+[^`]+`+"),
)

_URL_PATTERN = re.compile(
    r"https?://[^\s\])<>\"']+|www\.[^\s\])<>\"']+",
    re.I,
)

_UTM_PATTERN = re.compile(r"[?&]utm_[^&\s]+", re.I)

_EMPTY_MD_LINK = re.compile(r"\[[^\]]+\]\(\s*\)")

_GARBAGE_LINES = (
    re.compile(r"^\s*share\s+on\s+", re.I),
    re.compile(r"^\s*subscribe\s+to\s+", re.I),
    re.compile(r"^\s*read more\s*$", re.I),
    re.compile(r"^\s*click here\s*$", re.I),
    re.compile(r"^\s*loading\.{0,3}\s*$", re.I),
)


def strip_tracking_params(url: str) -> str:
    cleaned = _UTM_PATTERN.sub("", url)
    return cleaned.rstrip("?&")


def is_navigation_or_chrome(text: str) -> bool:
    blob = (text or "").strip()
    if len(blob) < 4:
        return True
    if any(pattern.search(blob) for pattern in _NAV_PATTERNS):
        return True
    return bool(_URL_PATTERN.fullmatch(blob))


def sanitize_evidence_statement(text: str, *, max_len: int = 500) -> str:
    """Remove navigation, markdown, raw URLs, and scrape garbage from customer text."""
    cleaned = " ".join((text or "").split())
    cleaned = _EMPTY_MD_LINK.sub("", cleaned)
    for pattern in _MARKDOWN_PATTERNS:
        cleaned = pattern.sub(r"\1" if pattern.groups else " ", cleaned)
    cleaned = _URL_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"[<>]", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    if is_navigation_or_chrome(cleaned):
        return ""
    return cleaned[:max_len]


def sanitize_source_body(text: str, *, max_len: int = 8000) -> str:
    """Sanitize fetched body before claim extraction."""
    lines: list[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or len(line) < 12:
            continue
        if any(p.match(line) for p in _GARBAGE_LINES):
            continue
        if is_navigation_or_chrome(line):
            continue
        lines.append(line)
    joined = " ".join(lines)
    joined = _URL_PATTERN.sub("", joined)
    joined = re.sub(r"\s{2,}", " ", joined).strip()
    return joined[:max_len]


def domain_from_url(url: str) -> str | None:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        return host or None
    except ValueError:
        return None
