"""Sensitive key detection — secrets must not live in agent config or LLM logs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.exceptions import InvalidStateError

SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "secret",
        "token",
        "password",
        "credentials",
        "authorization",
    },
)


SENSITIVE_SUFFIXES = (
    "_api_key",
    "_secret",
    "_token",
    "_password",
    "_credentials",
    "_authorization",
)


def _is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    if lower in SENSITIVE_KEYS:
        return True
    return any(lower.endswith(suffix) for suffix in SENSITIVE_SUFFIXES)


def find_sensitive_key(payload: Mapping[str, Any] | list[Any], *, path: str = "") -> str | None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_str = str(key)
            current_path = f"{path}.{key_str}" if path else key_str
            if _is_sensitive_key(key_str):
                return current_path
            if isinstance(value, (Mapping, list)):
                nested = find_sensitive_key(value, path=current_path)
                if nested is not None:
                    return nested
        return None

    if isinstance(payload, list):
        for index, item in enumerate(payload):
            current_path = f"{path}[{index}]"
            if isinstance(item, (Mapping, list)):
                nested = find_sensitive_key(item, path=current_path)
                if nested is not None:
                    return nested
        return None

    return None


def assert_no_sensitive_keys(payload: Mapping[str, Any] | list[Any]) -> None:
    sensitive_path = find_sensitive_key(payload)
    if sensitive_path is not None:
        raise InvalidStateError(f"Sensitive key not allowed in agent config: {sensitive_path}")


def redact_sensitive_payload(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            key_str = str(key)
            if _is_sensitive_key(key_str):
                redacted[key_str] = "***"
            else:
                redacted[key_str] = redact_sensitive_payload(value)
        return redacted
    if isinstance(payload, list):
        return [redact_sensitive_payload(item) for item in payload]
    return payload
