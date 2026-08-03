"""MCP security helpers — treat external content as untrusted."""

from __future__ import annotations

import re

_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"system\s+prompt", re.I),
    re.compile(r"<\s*script", re.I),
)


def sanitize_tool_output(text: str, *, max_len: int = 8000) -> str:
    cleaned = " ".join((text or "").split())
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered]", cleaned)
    return cleaned[:max_len]


def summarize_request(payload: dict) -> dict:
    out: dict = {}
    for key, value in payload.items():
        if key.lower() in {"key", "token", "secret", "authorization"}:
            continue
        if isinstance(value, str):
            out[key] = value[:500]
        elif isinstance(value, (int, float, bool)) or value is None:
            out[key] = value
    return out
