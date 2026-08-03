"""Prompt safety — sanitize context and block secrets in prompt payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.core.exceptions import InvalidStateError
from app.llm.errors import SECRET_MARKERS
from app.llm.secrets_boundary import assert_no_sensitive_keys, redact_sensitive_payload


class PromptBuildError(InvalidStateError):
    """Raised when prompt input contains unsafe or secret-bearing data."""


def _redact_secret_values(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in SECRET_MARKERS):
            return "[REDACTED]"
        return value
    if isinstance(value, Mapping):
        return {str(key): _redact_secret_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_secret_values(item) for item in value]
    return value


def sanitize_prompt_context(value: Any) -> Any:
    redacted = redact_sensitive_payload(value)
    return _redact_secret_values(redacted)


def assert_no_prompt_secrets(payload: Mapping[str, Any] | list[Any]) -> None:
    try:
        assert_no_sensitive_keys(payload)
    except InvalidStateError as exc:
        raise PromptBuildError(str(exc)) from exc


def format_context_block(label: str, context: Mapping[str, Any] | list[Any]) -> str:
    sanitized = sanitize_prompt_context(context)
    if isinstance(sanitized, (dict, list)):
        body = json.dumps(sanitized, ensure_ascii=True, sort_keys=True)
    else:
        body = str(sanitized)
    return f"{label}:\n{body}"
