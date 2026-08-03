"""Limit total tool-result bytes injected into follow-up LLM context."""

from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.tools.contracts import ToolResult
from app.tools.result_contracts import is_tool_result_envelope
from app.tools.result_messages import _compact_tool_result_payload

DEFAULT_TOOL_RESULTS_TOTAL_MAX_BYTES = 48_000


def get_tool_results_total_max_bytes() -> int:
    return get_settings().tool_results_total_max_bytes


def tool_result_message_size_bytes(result: ToolResult) -> int:
    payload = _compact_tool_result_payload(result)
    return len(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8"))


def compact_tool_result(result: ToolResult) -> ToolResult:
    output = result.output
    if isinstance(output, dict) and is_tool_result_envelope(output):
        meta_raw = output.get("meta")
        meta: dict[str, Any] = dict(meta_raw) if isinstance(meta_raw, dict) else {}
        meta["truncated"] = True
        compacted: dict[str, Any] = {
            "ok": output.get("ok"),
            "tool": output.get("tool"),
            "data": {
                "compact": True,
                "message": "Tool result compacted to fit context budget",
            },
            "meta": meta,
        }
        if compacted["ok"]:
            compacted.pop("error", None)
        else:
            compacted["error"] = output.get("error")
        return ToolResult(
            call_id=result.call_id,
            name=result.name,
            status=result.status,
            output=compacted,
            error=result.error,
            metadata={**result.metadata, "context_budget_compacted": True},
        )

    return ToolResult(
        call_id=result.call_id,
        name=result.name,
        status=result.status,
        output={
            "compact": True,
            "message": "Tool result compacted to fit context budget",
            "status": result.status,
        },
        error=result.error,
        metadata={**result.metadata, "context_budget_compacted": True},
    )


def apply_tool_results_context_budget(
    results: list[ToolResult],
    *,
    max_bytes: int | None = None,
) -> list[ToolResult]:
    limit = max_bytes if max_bytes is not None else get_tool_results_total_max_bytes()
    if not results:
        return results

    adjusted = list(results)

    def total_size() -> int:
        return sum(tool_result_message_size_bytes(result) for result in adjusted)

    if total_size() <= limit:
        return adjusted

    for index in sorted(
        range(len(adjusted)),
        key=lambda idx: tool_result_message_size_bytes(adjusted[idx]),
        reverse=True,
    ):
        if total_size() <= limit:
            break
        adjusted[index] = compact_tool_result(adjusted[index])

    return adjusted
