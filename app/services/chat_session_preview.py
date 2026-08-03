"""Chat session list previews (Phase AI.20) — computed from messages, not stored."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from app.core.security import sanitize_text
from app.db.models.agent_chat import AgentChatMessageTable
from app.schemas.contracts import AgentChatMessageRole

SESSION_PREVIEW_MAX_LENGTH = 160

_PREVIEW_ROLES = frozenset(
    {
        AgentChatMessageRole.USER,
        AgentChatMessageRole.ASSISTANT,
    },
)

_FORBIDDEN_PREVIEW_SUBSTRINGS = (
    "tool_logs",
    "technical_task_draft",
    "visual_brief",
    "api_key",
    "openai_api_key",
    "password",
    "secret",
)


@dataclass(frozen=True)
class SessionMessageUxStats:
    message_count: int = 0
    last_message_at: datetime | None = None
    last_message_preview: str | None = None
    unread_count: int = 0


def collapse_preview_line(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\r\n", " ").replace("\n", " ")).strip()


def build_message_preview(content: str) -> str | None:
    """
    Safe preview from user/assistant message content only (no metadata / drafts / tools).
    """
    sanitized = sanitize_text(content or "").strip()
    if not sanitized:
        return None

    collapsed = collapse_preview_line(sanitized)
    if not collapsed:
        return None

    lowered = collapsed.lower()
    if any(marker in lowered for marker in _FORBIDDEN_PREVIEW_SUBSTRINGS):
        return None

    if len(collapsed) <= SESSION_PREVIEW_MAX_LENGTH:
        return collapsed

    trimmed = collapsed[:SESSION_PREVIEW_MAX_LENGTH].rstrip()
    return f"{trimmed}…"


def build_preview_from_message(message: AgentChatMessageTable) -> str | None:
    if message.role not in _PREVIEW_ROLES:
        return None
    return build_message_preview(message.content)


def empty_session_ux_stats() -> SessionMessageUxStats:
    return SessionMessageUxStats(unread_count=0)
