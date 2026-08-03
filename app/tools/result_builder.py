"""Build and validate standardized tool result envelopes."""

from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.tools.execution_contracts import ToolExecutionResult, ToolExecutionStatus
from app.tools.result_contracts import (
    ToolExecutionErrorCode,
    ToolResultEnvelope,
    ToolResultError,
    ToolResultMeta,
)

DEFAULT_TOOL_RESULT_MAX_BYTES = 24_000

REASON_TO_ERROR_CODE: dict[str, ToolExecutionErrorCode] = {
    "invalid_tool_arguments": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "invalid_arguments": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "tool_not_allowed": ToolExecutionErrorCode.PERMISSION_DENIED,
    "tool_disabled": ToolExecutionErrorCode.PERMISSION_DENIED,
    "project_not_found": ToolExecutionErrorCode.NOT_FOUND,
    "task_not_found": ToolExecutionErrorCode.NOT_FOUND,
    "task_access_denied": ToolExecutionErrorCode.PERMISSION_DENIED,
    "brief_not_found": ToolExecutionErrorCode.NOT_FOUND,
    "brief_access_denied": ToolExecutionErrorCode.PERMISSION_DENIED,
    "asset_not_found": ToolExecutionErrorCode.NOT_FOUND,
    "asset_access_denied": ToolExecutionErrorCode.PERMISSION_DENIED,
    "asset_create_failed": ToolExecutionErrorCode.EXECUTION_FAILED,
    "project_access_denied": ToolExecutionErrorCode.PERMISSION_DENIED,
    "campaign_not_found": ToolExecutionErrorCode.NOT_FOUND,
    "campaign_archived": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "invalid_plan_payload": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "plan_draft_archived": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "plan_draft_generation_partial_state": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "missing_owner_id": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "missing_project_id": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "missing_agent_id": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "missing_agent_run_id": ToolExecutionErrorCode.INVALID_ARGUMENTS,
    "tool_call_limit_exceeded": ToolExecutionErrorCode.EXECUTION_FAILED,
    "tool_execution_disabled": ToolExecutionErrorCode.UNSUPPORTED_TOOL,
    "unsupported_tool": ToolExecutionErrorCode.UNSUPPORTED_TOOL,
    "result_too_large": ToolExecutionErrorCode.RESULT_TOO_LARGE,
}


def get_tool_result_max_bytes() -> int:
    settings = get_settings()
    return getattr(settings, "tool_result_max_bytes", DEFAULT_TOOL_RESULT_MAX_BYTES)


def _count_items(data: dict[str, Any]) -> int:
    if "count" in data and isinstance(data["count"], int):
        return data["count"]
    if "items" in data and isinstance(data["items"], list):
        return len(data["items"])
    if "active_agents" in data or "recent_tasks" in data or "recent_memory_summary" in data:
        return (
            len(data.get("active_agents") or [])
            + len(data.get("recent_tasks") or [])
            + len(data.get("recent_memory_summary") or [])
        )
    return 0


def envelope_to_dict(envelope: ToolResultEnvelope) -> dict[str, Any]:
    payload = envelope.model_dump(exclude_none=True)
    if envelope.error is None:
        payload.pop("error", None)
    return payload


def build_tool_success(
    tool_name: str,
    data: dict[str, Any],
    *,
    meta: ToolResultMeta | None = None,
) -> dict[str, Any]:
    resolved_meta = meta or ToolResultMeta(
        truncated=False,
        items_count=_count_items(data),
    )
    envelope = ToolResultEnvelope(
        ok=True,
        tool=tool_name,
        data=data,
        meta=resolved_meta,
    )
    return envelope_to_dict(envelope)


def build_tool_error(
    tool_name: str,
    *,
    code: ToolExecutionErrorCode,
    message: str,
    meta: ToolResultMeta | None = None,
) -> dict[str, Any]:
    envelope = ToolResultEnvelope(
        ok=False,
        tool=tool_name,
        error=ToolResultError(code=code, message=message),
        meta=meta or ToolResultMeta(),
    )
    return envelope_to_dict(envelope)


def envelope_size_bytes(envelope: dict[str, Any]) -> int:
    return len(json.dumps(envelope, ensure_ascii=True, sort_keys=True).encode("utf-8"))


def enforce_result_size_limit(
    envelope: dict[str, Any],
    *,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    limit = max_bytes if max_bytes is not None else get_tool_result_max_bytes()
    if envelope_size_bytes(envelope) <= limit:
        return envelope

    tool_name = str(envelope.get("tool", "unknown"))
    return build_tool_error(
        tool_name,
        code=ToolExecutionErrorCode.RESULT_TOO_LARGE,
        message="Tool result exceeds size limit",
    )


def _error_code_from_execution(execution: ToolExecutionResult) -> ToolExecutionErrorCode:
    if execution.reason and execution.reason in REASON_TO_ERROR_CODE:
        return REASON_TO_ERROR_CODE[execution.reason]

    error_payload = execution.error_payload or {}
    error_type = str(error_payload.get("error_type", ""))
    if "NotFound" in error_type or execution.reason == "project_not_found":
        return ToolExecutionErrorCode.NOT_FOUND
    if "Validation" in error_type or "Invalid" in error_type:
        return ToolExecutionErrorCode.INVALID_ARGUMENTS
    if "NotAllowed" in error_type or "Denied" in error_type:
        return ToolExecutionErrorCode.PERMISSION_DENIED
    return ToolExecutionErrorCode.EXECUTION_FAILED


def envelope_from_execution(execution: ToolExecutionResult) -> dict[str, Any]:
    tool_name = execution.tool_name

    if execution.status == ToolExecutionStatus.SUCCEEDED:
        data = dict(execution.output_payload or {})
        envelope = build_tool_success(
            tool_name,
            data,
            meta=ToolResultMeta(truncated=False, items_count=_count_items(data)),
        )
        return enforce_result_size_limit(envelope)

    message = "Tool execution failed"
    if execution.error_payload:
        message = str(execution.error_payload.get("safe_message") or message)

    envelope = build_tool_error(
        tool_name,
        code=_error_code_from_execution(execution),
        message=message,
    )
    return enforce_result_size_limit(envelope)
