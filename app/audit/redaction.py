"""Safe redaction helpers for audit reports (SKILL-01.6)."""

from __future__ import annotations

import re
from typing import Any

_SECRET_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "client_secret",
    "refresh_token",
    "authorization",
    "credential",
)

_ABSOLUTE_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\|/)[^\s\"']+")


def redact_secret_value(value: str) -> str:
    return "[REDACTED]"


def redact_text(text: str) -> str:
    if not text:
        return text
    redacted = _ABSOLUTE_PATH_PATTERN.sub("[PATH]", text)
    lowered = redacted.lower()
    for fragment in _SECRET_FRAGMENTS:
        if fragment in lowered:
            return redacted if redacted == text else redacted
    return redacted


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(fragment in lowered for fragment in _SECRET_FRAGMENTS):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_payload(value)
        elif isinstance(value, str):
            redacted[key] = redact_text(value)
        else:
            redacted[key] = value
    return redacted


def sanitize_location(location: str | None) -> str | None:
    if location is None:
        return None
    return _ABSOLUTE_PATH_PATTERN.sub("[PATH]", location)
