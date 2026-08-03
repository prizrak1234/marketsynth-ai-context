"""Chat search helpers (Phase AI.24) — SQL LIKE only, no semantic retrieval."""

from __future__ import annotations

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.services.chat_session_preview import collapse_preview_line

CHAT_SEARCH_QUERY_MIN_LENGTH = 2
CHAT_SEARCH_QUERY_MAX_LENGTH = 120
CHAT_SEARCH_PREVIEW_MAX_LENGTH = 200
_LIKE_ESCAPE_CHAR = "\\"


def escape_like_pattern(value: str) -> str:
    """Escape SQL LIKE wildcards so user input is matched literally."""
    return (
        value.replace(_LIKE_ESCAPE_CHAR, _LIKE_ESCAPE_CHAR + _LIKE_ESCAPE_CHAR)
        .replace("%", _LIKE_ESCAPE_CHAR + "%")
        .replace("_", _LIKE_ESCAPE_CHAR + "_")
    )


def build_like_pattern(query: str) -> str:
    return f"%{escape_like_pattern(query)}%"


def prepare_search_query(raw: str | None, *, required: bool = False) -> str | None:
    if raw is None or not str(raw).strip():
        if required:
            raise InvalidStateError("Search query is required")
        return None
    cleaned = sanitize_text(str(raw)).strip()
    if len(cleaned) < CHAT_SEARCH_QUERY_MIN_LENGTH:
        raise InvalidStateError(
            f"Search query must be at least {CHAT_SEARCH_QUERY_MIN_LENGTH} characters",
        )
    if len(cleaned) > CHAT_SEARCH_QUERY_MAX_LENGTH:
        raise InvalidStateError(
            f"Search query must be at most {CHAT_SEARCH_QUERY_MAX_LENGTH} characters",
        )
    return cleaned


def build_search_content_preview(content: str) -> str:
    """Safe preview for search hits — content column only, PII-sanitized."""
    sanitized = sanitize_text(content or "").strip()
    if not sanitized:
        return ""
    collapsed = collapse_preview_line(sanitized)
    if len(collapsed) <= CHAT_SEARCH_PREVIEW_MAX_LENGTH:
        return collapsed
    return collapsed[: CHAT_SEARCH_PREVIEW_MAX_LENGTH - 1].rstrip() + "…"

