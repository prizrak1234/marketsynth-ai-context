"""Sanitize chat audit safe_metadata (Phase AI.25)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

_FORBIDDEN_KEYS = frozenset(
    {
        "content",
        "message",
        "query",
        "body",
        "title",
        "text",
        "markdown",
        "output",
        "output_payload",
        "input_payload",
        "prompt",
        "messages",
        "raw_response",
        "tool_results",
        "technical_task_draft",
        "visual_brief",
        "marketing_brief",
        "content_plan",
        "message_metadata",
        "execution_metadata",
        "api_key",
        "secret",
        "password",
        "token",
    },
)

_ALLOWED_SCALAR_TYPES = (bool, int, float, str, type(None))


def _coerce_safe_value(value: Any) -> Any:
    if isinstance(value, (bool, int, float, type(None))):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in ("secret", "password", "api_key", "token")):
            return "[redacted]"
        return value[:256]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        safe_items = [_coerce_safe_value(item) for item in value[:20]]
        return [item for item in safe_items if isinstance(item, _ALLOWED_SCALAR_TYPES)]
    if isinstance(value, dict):
        return build_safe_metadata(value)
    return None


def build_safe_metadata(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    safe: dict[str, Any] = {}
    for key, value in data.items():
        normalized = str(key).strip().lower()
        if normalized in _FORBIDDEN_KEYS:
            continue
        coerced = _coerce_safe_value(value)
        if coerced is None:
            continue
        if isinstance(coerced, dict) and not coerced:
            continue
        safe[normalized] = coerced
    return safe
