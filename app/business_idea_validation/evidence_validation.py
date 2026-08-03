"""CWF.1 — strict evidence acceptance rules for commercial reports."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.business_idea_validation.sanitization import (
    is_navigation_or_chrome,
    sanitize_evidence_statement,
)

_EMPTY_MD_LINK = re.compile(r"\[[^\]]+\]\(\s*\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")

_BOILERPLATE_PATTERNS = (
    re.compile(r"\bрейтинг\s+компаний\b", re.I),
    re.compile(r"\bтоп\s*стартап", re.I),
    re.compile(r"\bcrm\s+и\s+продаж", re.I),
    re.compile(r"\bавтоматизация\s+(?:бизнес|бухгалтер|документо)", re.I),
    re.compile(r"\bаналитика\s+и\s+продажи\s+на\s+маркетплейс", re.I),
    re.compile(r"\b\d+\s+компаний\s+в\s+основном\s+рейтинге\b", re.I),
    re.compile(r"\bсредний\s+рост\s+выручки\b", re.I),
    re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", re.I),
    re.compile(r"\ball\s+categories\b|\bview\s+all\b", re.I),
)

_CATEGORY_MENU_DENSITY = re.compile(
    r"(?:CRM|HR|HoReCa|маркетплейс|бухгалтер|документооборот|Telegram|Instagram){3,}",
    re.I,
)


def is_valid_source_url(url: str | None) -> bool:
    if not url or not url.strip():
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def has_empty_markdown_links(text: str) -> bool:
    return bool(_EMPTY_MD_LINK.search(text or ""))


def is_boilerplate_content(text: str) -> bool:
    blob = (text or "").strip()
    if len(blob) < 20:
        return True
    if has_empty_markdown_links(blob):
        return True
    if _CATEGORY_MENU_DENSITY.search(blob):
        return True
    if sum(1 for p in _BOILERPLATE_PATTERNS if p.search(blob)) >= 2:
        return True
    # Long concatenated nav without sentence structure
    if len(blob) > 180 and blob.count(" ") > 25 and "." not in blob[:120]:
        alpha_chunks = [w for w in blob.split() if len(w) > 2]
        if len(alpha_chunks) > 18 and len(set(alpha_chunks)) / len(alpha_chunks) < 0.55:
            return True
    return False


def clean_excerpt_for_finding(text: str, *, max_len: int = 320) -> str:
    cleaned = sanitize_evidence_statement(text, max_len=max_len * 2)
    cleaned = _EMPTY_MD_LINK.sub("", cleaned)
    for match in _MD_LINK.finditer(cleaned):
        label, href = match.group(1), match.group(2).strip()
        if not href:
            cleaned = cleaned.replace(match.group(0), label)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    if is_navigation_or_chrome(cleaned) or is_boilerplate_content(cleaned):
        return ""
    return cleaned[:max_len]


def validate_evidence_acceptance(
    *,
    observation: str,
    source_url: str | None,
    source_title: str | None = None,
) -> tuple[bool, str | None]:
    """Return (accepted, rejection_reason)."""
    if not is_valid_source_url(source_url):
        return False, "missing_url"
    excerpt = clean_excerpt_for_finding(observation)
    if not excerpt or len(excerpt) < 24:
        return False, "empty_or_navigation_excerpt"
    if is_boilerplate_content(excerpt):
        return False, "boilerplate_content"
    if has_empty_markdown_links(observation):
        return False, "empty_markdown_link"
    title = (source_title or "").strip()
    if title and len(title) < 3:
        return False, "invalid_source_title"
    return True, None
