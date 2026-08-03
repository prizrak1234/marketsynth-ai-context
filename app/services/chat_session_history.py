"""Session-scoped chat history for agent runs (Phase AI.19) — not long-term memory."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.security import sanitize_text
from app.db.models.agent_chat import AgentChatMessageTable
from app.prompts.safety import sanitize_prompt_context
from app.schemas.contracts import AgentChatMessageRole

_HISTORY_ROLES = frozenset(
    {
        AgentChatMessageRole.USER,
        AgentChatMessageRole.ASSISTANT,
    },
)

_FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "tool_logs",
        "tools",
        "tool_results",
        "config",
        "settings",
        "api_key",
        "openai_api_key",
        "anthropic_api_key",
        "secret",
        "password",
        "token",
    },
)


def agent_chat_session_history_limit() -> int:
    return get_settings().agent_chat_session_history_limit


def _safe_message_content(content: str) -> str:
    return sanitize_text(content).strip()


def build_session_history_for_run(
    prior_messages: list[AgentChatMessageTable],
    *,
    current_user_content: str,
    limit: int | None = None,
) -> list[dict[str, str]]:
    """
    Build recent turn history for LLM input (role + content only).
    Excludes system messages, tool logs, secrets, and configs.
    """
    max_messages = limit if limit is not None else agent_chat_session_history_limit()
    prior_turns = [
        message
        for message in prior_messages
        if message.role in _HISTORY_ROLES and _safe_message_content(message.content)
    ]
    slots_for_prior = max(0, max_messages - 1)
    selected_prior = prior_turns[-slots_for_prior:] if slots_for_prior else []

    history: list[dict[str, str]] = []
    for message in selected_prior:
        history.append(
            {
                "role": message.role.value,
                "content": _safe_message_content(message.content),
            },
        )
    history.append({"role": AgentChatMessageRole.USER.value, "content": current_user_content})
    return history[-max_messages:]


def assert_history_safe_for_prompt(history: list[dict[str, Any]]) -> None:
    """Guardrail: session history must not carry tool logs or secret-bearing keys."""
    sanitized = sanitize_prompt_context(history)
    if not isinstance(sanitized, list):
        return
    for item in sanitized:
        if not isinstance(item, dict):
            continue
        lowered_keys = {str(key).lower() for key in item}
        assert not lowered_keys & _FORBIDDEN_METADATA_KEYS
        for key in item:
            if str(key).lower() in _FORBIDDEN_METADATA_KEYS:
                raise ValueError(f"Forbidden history key: {key}")
