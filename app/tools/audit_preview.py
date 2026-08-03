"""Build safe audit previews from tool calls and results."""

from __future__ import annotations

import json
from typing import Any

from app.tools.audit_contracts import ToolExecutionAuditPreview
from app.tools.contracts import ToolCall, ToolResult
from app.tools.marketing_tools import (
    CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME,
    CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME,
    CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
)
from app.tools.result_contracts import is_tool_result_envelope
from app.tools.security import sanitize_tool_payload

MAX_ARGUMENT_STRING_LENGTH = 256
MAX_ARGUMENTS_PREVIEW_BYTES = 2_048
_TRUNCATION_MARKER = "...[truncated]"


def _truncate_string(value: str, *, max_length: int = MAX_ARGUMENT_STRING_LENGTH) -> str:
    if len(value) <= max_length:
        return value
    marker = _TRUNCATION_MARKER
    return f"{value[: max_length - len(marker)]}{marker}"


def _truncate_preview_value(value: Any) -> Any:
    if isinstance(value, str):
        return _truncate_string(value)
    if isinstance(value, dict):
        return {str(key): _truncate_preview_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_truncate_preview_value(item) for item in value[:20]]
    return value


def _enforce_preview_size(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    if len(encoded) <= MAX_ARGUMENTS_PREVIEW_BYTES:
        return payload

    compact = {"preview_truncated": True}
    for key, value in payload.items():
        compact[key] = _truncate_preview_value(value)
        candidate = json.dumps(compact, ensure_ascii=True, sort_keys=True).encode("utf-8")
        if len(candidate) > MAX_ARGUMENTS_PREVIEW_BYTES:
            compact[key] = _TRUNCATION_MARKER
    return compact


def _build_create_draft_arguments_preview(arguments: dict[str, Any]) -> dict[str, Any]:
    body = arguments.get("body")
    preview: dict[str, Any] = {}
    for key in ("brief_id", "type", "title"):
        if key in arguments:
            preview[key] = arguments[key]
    if isinstance(body, str):
        preview["body_length"] = len(body)
    metadata = arguments.get("metadata")
    if isinstance(metadata, dict):
        preview["metadata_keys"] = list(metadata.keys())[:20]
    return _enforce_preview_size(sanitize_tool_payload(preview))


def build_arguments_preview(
    arguments: dict[str, Any],
    *,
    tool_name: str | None = None,
) -> dict[str, Any]:
    if tool_name == CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME:
        return _build_create_draft_arguments_preview(arguments)

    sanitized = sanitize_tool_payload(dict(arguments))
    truncated = _truncate_preview_value(sanitized)
    if not isinstance(truncated, dict):
        return {"value": truncated}
    return _enforce_preview_size(truncated)


def _build_create_draft_result_preview(result: ToolResult) -> dict[str, Any]:
    preview: dict[str, Any] = {
        "status": result.status,
        "tool_name": result.name,
    }
    if isinstance(result.output, dict) and is_tool_result_envelope(result.output):
        preview["ok"] = result.output.get("ok")
        if result.output.get("ok"):
            data = result.output.get("data") or {}
            asset = data.get("asset") if isinstance(data, dict) else None
            if isinstance(asset, dict):
                preview["asset_id"] = asset.get("id")
                preview["status"] = asset.get("status")
        else:
            error = result.output.get("error") or {}
            if error.get("code"):
                preview["error_code"] = error["code"]
    return preview


def _build_plan_draft_create_result_preview(result: ToolResult) -> dict[str, Any]:
    preview: dict[str, Any] = {
        "status": result.status,
        "tool_name": result.name,
    }
    if isinstance(result.output, dict) and is_tool_result_envelope(result.output):
        preview["ok"] = result.output.get("ok")
        if result.output.get("ok"):
            data = result.output.get("data") or {}
            draft = data.get("draft") if isinstance(data, dict) else None
            if isinstance(draft, dict):
                preview["draft_id"] = draft.get("draft_id")
                preview["campaign_id"] = draft.get("campaign_id")
    return preview


def _build_plan_draft_generate_assets_result_preview(result: ToolResult) -> dict[str, Any]:
    preview: dict[str, Any] = {
        "status": result.status,
        "tool_name": result.name,
    }
    if isinstance(result.output, dict) and is_tool_result_envelope(result.output):
        preview["ok"] = result.output.get("ok")
        if result.output.get("ok"):
            data = result.output.get("data") or {}
            if isinstance(data, dict):
                if "created_count" in data:
                    preview["created_count"] = data.get("created_count")
                if "already_generated" in data:
                    preview["already_generated"] = data.get("already_generated")
                asset_ids = data.get("asset_ids")
                if isinstance(asset_ids, list):
                    preview["asset_ids"] = [str(item) for item in asset_ids[:50]]
        else:
            error = result.output.get("error") or {}
            if error.get("code"):
                preview["error_code"] = error["code"]
    return preview


def _build_create_revision_result_preview(result: ToolResult) -> dict[str, Any]:
    preview: dict[str, Any] = {
        "status": result.status,
        "tool_name": result.name,
    }
    if isinstance(result.output, dict) and is_tool_result_envelope(result.output):
        preview["ok"] = result.output.get("ok")
        if result.output.get("ok"):
            data = result.output.get("data") or {}
            if isinstance(data, dict):
                if data.get("asset_id") is not None:
                    preview["asset_id"] = data.get("asset_id")
                if data.get("current_version_number") is not None:
                    preview["current_version_number"] = data.get("current_version_number")
        else:
            error = result.output.get("error") or {}
            if error.get("code"):
                preview["error_code"] = error["code"]
    return preview


def build_result_preview(result: ToolResult) -> dict[str, Any]:
    if result.name == CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME:
        return _build_create_draft_result_preview(result)
    if result.name == CONTENT_ASSET_CREATE_REVISION_TOOL_NAME:
        return _build_create_revision_result_preview(result)
    if result.name == CAMPAIGN_PLAN_DRAFT_CREATE_TOOL_NAME:
        return _build_plan_draft_create_result_preview(result)
    if result.name == CAMPAIGN_PLAN_DRAFT_GENERATE_ASSETS_TOOL_NAME:
        return _build_plan_draft_generate_assets_result_preview(result)

    preview: dict[str, Any] = {
        "status": result.status,
        "tool_name": result.name,
    }
    if isinstance(result.output, dict) and is_tool_result_envelope(result.output):
        preview["ok"] = result.output.get("ok")
        meta = result.output.get("meta") or {}
        items_count = meta.get("items_count")
        if items_count is not None:
            preview["items_count"] = items_count
        if meta.get("truncated"):
            preview["truncated"] = True
        error = result.output.get("error") or {}
        if error.get("code"):
            preview["error_code"] = error["code"]
        return preview

    if isinstance(result.output, dict):
        count = result.output.get("count")
        if count is not None:
            preview["count"] = count
        reason = result.output.get("reason")
        if reason is not None:
            preview["reason"] = reason
    result_count = result.metadata.get("result_count")
    if result_count is not None and "count" not in preview and "items_count" not in preview:
        preview["count"] = result_count
    reason = result.metadata.get("reason")
    if reason is not None and "reason" not in preview:
        preview["reason"] = reason
    return preview


def build_error_preview(error: dict[str, Any] | None) -> dict[str, Any] | None:
    if not error:
        return None
    preview: dict[str, Any] = {}
    error_type = error.get("error_type")
    if error_type is not None:
        preview["error_type"] = error_type
    safe_message = error.get("safe_message")
    if safe_message is not None:
        preview["safe_message"] = safe_message
    reason = error.get("reason")
    if reason is not None:
        preview["reason"] = reason
    return preview or None


def build_audit_preview(tool_call: ToolCall, result: ToolResult) -> ToolExecutionAuditPreview:
    return ToolExecutionAuditPreview(
        arguments_preview=build_arguments_preview(
            tool_call.arguments,
            tool_name=tool_call.name,
        ),
        result_preview=build_result_preview(result),
        error_preview=build_error_preview(result.error),
    )
