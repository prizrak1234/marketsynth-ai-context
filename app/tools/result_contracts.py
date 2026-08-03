"""Standard tool result envelope contracts for real read-only tools."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ToolExecutionErrorCode(StrEnum):
    INVALID_ARGUMENTS = "invalid_arguments"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    EXECUTION_FAILED = "execution_failed"
    RESULT_TOO_LARGE = "result_too_large"
    UNSUPPORTED_TOOL = "unsupported_tool"


class ToolResultError(BaseModel):
    code: ToolExecutionErrorCode
    message: str


class ToolResultMeta(BaseModel):
    truncated: bool = False
    items_count: int = 0


class ToolResultEnvelope(BaseModel):
    ok: bool
    tool: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: ToolResultError | None = None
    meta: ToolResultMeta = Field(default_factory=ToolResultMeta)


def is_tool_result_envelope(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    return "ok" in payload and "tool" in payload
