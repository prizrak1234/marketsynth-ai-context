"""Compact sub-agent output for sequential chain step transfer (Phase AI.14)."""

from __future__ import annotations

import json
from typing import Any

from app.agents.marketer.chains import COMPACT_SUBAGENT_OUTPUT_MAX_BYTES
from app.core.security import sanitize_text


def compact_subagent_output(output_payload: dict[str, Any] | None) -> dict[str, Any]:
    """
    Build a small JSON-safe dict for the next child run (not full parent context).

    Enforces COMPACT_SUBAGENT_OUTPUT_MAX_BYTES on serialized size.
    """
    payload = dict(output_payload or {})
    tools = payload.get("tools") if isinstance(payload.get("tools"), dict) else {}
    tool_names = tools.get("tool_names") if isinstance(tools.get("tool_names"), list) else []

    compact: dict[str, Any] = {
        "content": sanitize_text(str(payload.get("content", ""))).strip(),
        "tool_names": [str(name) for name in tool_names[:20]],
    }

    serialized = json.dumps(compact, ensure_ascii=False)
    if len(serialized.encode("utf-8")) <= COMPACT_SUBAGENT_OUTPUT_MAX_BYTES:
        return compact

    while compact["content"] and len(
        json.dumps(compact, ensure_ascii=False).encode("utf-8"),
    ) > COMPACT_SUBAGENT_OUTPUT_MAX_BYTES:
        compact["content"] = compact["content"][: max(0, len(compact["content"]) - 256)]

    if len(json.dumps(compact, ensure_ascii=False).encode("utf-8")) > COMPACT_SUBAGENT_OUTPUT_MAX_BYTES:
        compact = {"content": compact["content"][:512], "tool_names": []}

    return compact
