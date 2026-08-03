"""Deterministic chat session titles (Phase AI.20) — no LLM."""

from __future__ import annotations

import re

from app.schemas.contracts import ChatSessionDomain

SESSION_TITLE_MAX_LENGTH = 80

_DOMAIN_TITLE_FALLBACKS: dict[ChatSessionDomain, str] = {
    ChatSessionDomain.UNKNOWN: "General chat",
    ChatSessionDomain.MARKETING: "Marketing chat",
    ChatSessionDomain.PROGRAMMER: "Programmer chat",
    ChatSessionDomain.MEDIA: "Media chat",
}


def collapse_message_line(text: str) -> str:
    """Collapse multiline user input into a single trimmed line."""
    collapsed = re.sub(r"\s+", " ", (text or "").replace("\r\n", " ").replace("\n", " "))
    return collapsed.strip()


def build_session_title(
    *,
    first_message: str | None,
    domain: ChatSessionDomain,
    provided_title: str | None = None,
) -> str:
    """
    Build a deterministic session title from the first user message or domain fallback.
    """
    if provided_title is not None:
        explicit = collapse_message_line(provided_title)
        if explicit:
            return _truncate_title(explicit)

    from_message = collapse_message_line(first_message or "")
    if from_message:
        return _truncate_title(from_message)

    return _DOMAIN_TITLE_FALLBACKS[domain]


def _truncate_title(text: str) -> str:
    if len(text) <= SESSION_TITLE_MAX_LENGTH:
        return text
    trimmed = text[:SESSION_TITLE_MAX_LENGTH].rstrip()
    return f"{trimmed}…"
