"""Phase 2.23 — total tool-result context budget."""

from __future__ import annotations

import json

from app.tools.context_budget import (
    apply_tool_results_context_budget,
    compact_tool_result,
    tool_result_message_size_bytes,
)
from app.tools.contracts import ToolCall, ToolResult
from app.tools.result_builder import build_tool_success
from app.tools.result_messages import build_tool_result_message


def test_compact_tool_result_sets_meta_truncated() -> None:
    envelope = build_tool_success(
        "memory.search",
        {"items": [{"id": "1", "content_preview": "x" * 5000}], "count": 1},
    )
    result = ToolResult(
        call_id="call_1",
        name="memory.search",
        status="succeeded",
        output=envelope,
    )
    compacted = compact_tool_result(result)
    assert isinstance(compacted.output, dict)
    assert compacted.output["meta"]["truncated"] is True
    assert compacted.output["data"]["compact"] is True
    assert tool_result_message_size_bytes(compacted) < tool_result_message_size_bytes(result)


def test_total_budget_compacts_largest_results_first() -> None:
    big = ToolResult(
        call_id="call_big",
        name="memory.search",
        status="succeeded",
        output=build_tool_success(
            "memory.search",
            {"items": [{"content_preview": "z" * 8000}], "count": 1},
        ),
    )
    small = ToolResult(
        call_id="call_small",
        name="task.list_recent",
        status="succeeded",
        output=build_tool_success("task.list_recent", {"tasks": [], "count": 0}),
    )
    budgeted = apply_tool_results_context_budget([big, small], max_bytes=2_000)
    assert budgeted[0].metadata.get("context_budget_compacted") is True
    total = sum(tool_result_message_size_bytes(result) for result in budgeted)
    assert total <= 2_000


def test_tool_result_message_remains_valid_json() -> None:
    envelope = build_tool_success(
        "project_context.get",
        {"project": {"name": "Demo"}, "agents": [], "tasks": []},
    )
    result = ToolResult(
        call_id="call_ctx",
        name="project_context.get",
        status="succeeded",
        output=envelope,
    )
    budgeted = apply_tool_results_context_budget([result], max_bytes=200)
    message = build_tool_result_message(
        ToolCall(id="call_ctx", name="project_context.get", arguments={}),
        budgeted[0],
    )
    payload = json.loads(message.content or "")
    assert payload["ok"] is True or payload.get("status") == "succeeded"
