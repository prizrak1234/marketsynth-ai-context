"""Tool payload safety — block secrets in arguments, redact results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.tools.contracts import ToolResult
from app.tools.errors import ToolValidationError

SECRET_VALUE_MARKERS = ("sk-", "api_key", "authorization", "bearer ")

FORBIDDEN_TOOL_KEYS = frozenset(
    {
        "api_key",
        "secret",
        "token",
        "password",
        "credential",
        "credentials",
        "authorization",
        "cookie",
    },
)

FORBIDDEN_TOOL_SUFFIXES = (
    "_api_key",
    "_secret",
    "_token",
    "_password",
    "_credential",
    "_credentials",
    "_authorization",
    "_cookie",
)


def _is_forbidden_key(key: str) -> bool:
    lower = key.lower()
    if lower in FORBIDDEN_TOOL_KEYS:
        return True
    return any(lower.endswith(suffix) for suffix in FORBIDDEN_TOOL_SUFFIXES)


def find_forbidden_tool_key(
    payload: Mapping[str, Any] | list[Any],
    *,
    path: str = "",
) -> str | None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_str = str(key)
            current_path = f"{path}.{key_str}" if path else key_str
            if _is_forbidden_key(key_str):
                return current_path
            if isinstance(value, (Mapping, list)):
                nested = find_forbidden_tool_key(value, path=current_path)
                if nested is not None:
                    return nested
        return None

    if isinstance(payload, list):
        for index, item in enumerate(payload):
            current_path = f"{path}[{index}]"
            if isinstance(item, (Mapping, list)):
                nested = find_forbidden_tool_key(item, path=current_path)
                if nested is not None:
                    return nested
        return None

    return None


def _redact_secret_values(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in SECRET_VALUE_MARKERS):
            return "[REDACTED]"
        return value
    if isinstance(value, Mapping):
        return {str(key): _redact_secret_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_secret_values(item) for item in value]
    return value


def sanitize_tool_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        key_str = str(key)
        if _is_forbidden_key(key_str):
            redacted[key_str] = "[REDACTED]"
        elif isinstance(value, Mapping):
            redacted[key_str] = sanitize_tool_payload(dict(value))
        elif isinstance(value, list):
            redacted[key_str] = [
                sanitize_tool_payload(dict(item))
                if isinstance(item, Mapping)
                else _redact_secret_values(item)
                for item in value
            ]
        else:
            redacted[key_str] = _redact_secret_values(value)
    return redacted


def assert_no_tool_secrets(payload: dict[str, Any]) -> None:
    forbidden_path = find_forbidden_tool_key(payload)
    if forbidden_path is not None:
        raise ToolValidationError(
            f"Sensitive key not allowed in tool arguments: {forbidden_path}",
            original_error_type="ForbiddenToolKey",
        )


def sanitize_tool_result(result: ToolResult) -> ToolResult:
    output = result.output
    if isinstance(output, dict):
        output = sanitize_tool_payload(output)
    elif isinstance(output, str):
        output = _redact_secret_values(output)

    error = result.error
    if isinstance(error, dict):
        error = sanitize_tool_payload(error)

    metadata = sanitize_tool_payload(result.metadata) if result.metadata else {}

    return result.model_copy(
        update={
            "output": output,
            "error": error,
            "metadata": metadata,
        },
    )
