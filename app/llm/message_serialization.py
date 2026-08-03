"""Serialize LLM messages for OpenAI/LiteLLM-compatible providers."""

from __future__ import annotations

from typing import Any

from app.llm.contracts import LLMMessage


def llm_message_to_provider_dict(message: LLMMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": message.role}
    if message.role == "tool":
        payload["tool_call_id"] = message.tool_call_id
        payload["name"] = message.name
        payload["content"] = message.content or ""
        return payload

    if message.tool_calls:
        payload["content"] = message.content
        payload["tool_calls"] = message.tool_calls
        return payload

    payload["content"] = message.content or ""
    return payload
