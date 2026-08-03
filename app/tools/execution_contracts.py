"""Tool execution contracts — inputs, results, and structured errors."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.tools.permissions import ToolExecutionMode


class ToolExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ToolExecutionError(BaseModel):
    error_type: str
    safe_message: str
    reason: str | None = None


class ToolCallInput(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str | None = None


class ToolExecutionResult(BaseModel):
    tool_name: str
    status: ToolExecutionStatus
    output_payload: dict[str, Any] | None = None
    error_payload: dict[str, Any] | None = None
    reason: str | None = None
    execution_mode: ToolExecutionMode
    request_id: UUID | None = None
    run_id: UUID | None = None
    agent_id: UUID | None = None
