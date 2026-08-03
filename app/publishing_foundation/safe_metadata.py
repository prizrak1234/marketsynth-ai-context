"""Sanitize publishing job metadata and audit payloads (Phase AI.64)."""

from __future__ import annotations

from typing import Any

_FORBIDDEN_KEYS = frozenset(
    {
        "token",
        "secret",
        "api_key",
        "authorization",
        "password",
        "raw_response",
        "response_body",
        "body",
        "payload",
        "payload_snapshot",
        "b64_json",
        "base64",
    },
)

_MAX_STRING_LEN = 512


def _scrub_value(key: str, value: object) -> object | None:
    key_lower = key.lower()
    if key_lower in _FORBIDDEN_KEYS:
        return None
    if isinstance(value, str):
        if len(value) > _MAX_STRING_LEN:
            return value[:_MAX_STRING_LEN] + "…"
        return value
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, dict):
        return sanitize_publishing_metadata(value)
    return None


def sanitize_publishing_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        scrubbed = _scrub_value(str(key), value)
        if scrubbed is not None:
            cleaned[str(key)] = scrubbed
    return cleaned
