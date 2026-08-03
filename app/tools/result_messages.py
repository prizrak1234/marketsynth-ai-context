"""Build LLM tool result messages for follow-up provider calls."""

from __future__ import annotations

import json
from typing import Any

from app.llm.contracts import LLMMessage
from app.tools.contracts import ToolCall, ToolResult
from app.tools.result_contracts import is_tool_result_envelope

MAX_TOOL_RESULT_CONTENT_BYTES = 16_384
_TRUNCATION_MARKER = "...[truncated]"


def build_assistant_tool_call_message(
    tool_calls: list[ToolCall],
    *,
    content: str | None = None,
) -> LLMMessage:
    provider_tool_calls: list[dict[str, Any]] = []
    for index, call in enumerate(tool_calls):
        call_id = call.id or f"call_{call.name}_{index}"
        provider_tool_calls.append(
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments, ensure_ascii=True, sort_keys=True),
                },
            },
        )
    return LLMMessage(
        role="assistant",
        content=content,
        tool_calls=provider_tool_calls,
    )


def _compact_tool_result_payload(result: ToolResult) -> dict[str, Any]:
    if isinstance(result.output, dict) and is_tool_result_envelope(result.output):
        return result.output

    if result.status == "succeeded" and isinstance(result.output, dict):
        return {
            "status": "succeeded",
            "output": result.output,
        }

    if result.status == "skipped":
        reason = result.metadata.get("reason")
        if isinstance(result.output, dict) and result.output.get("reason"):
            reason = result.output.get("reason")
        return {
            "status": "skipped",
            "reason": reason or "tool_skipped",
        }

    error = result.error or {}
    return {
        "status": "failed",
        "reason": result.metadata.get("reason") or error.get("error_type") or "tool_failed",
        "safe_message": error.get("safe_message"),
    }


def _truncate_tool_content(content: str) -> str:
    encoded = content.encode("utf-8")
    if len(encoded) <= MAX_TOOL_RESULT_CONTENT_BYTES:
        return content

    marker_bytes = _TRUNCATION_MARKER.encode("utf-8")
    max_body = MAX_TOOL_RESULT_CONTENT_BYTES - len(marker_bytes)
    truncated = encoded[:max_body].decode("utf-8", errors="ignore")
    return f"{truncated}{_TRUNCATION_MARKER}"


def build_tool_result_message(tool_call: ToolCall, result: ToolResult) -> LLMMessage:
    payload = _compact_tool_result_payload(result)
    content = _truncate_tool_content(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    call_id = tool_call.id or f"call_{tool_call.name}"
    return LLMMessage(
        role="tool",
        tool_call_id=call_id,
        name=tool_call.name,
        content=content,
    )


def truncate_tool_result_content(content: str) -> str:
    return _truncate_tool_content(content)
