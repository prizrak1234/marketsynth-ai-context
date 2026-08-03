"""Tool execution audit contracts — safe previews only, no raw memory content."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

ToolExecutionLogStatus = Literal["succeeded", "failed", "skipped"]
ToolExecutionLogMode = Literal["disabled", "no_op", "read_only", "write"]


class ToolAuditTracker(BaseModel):
    logged_count: int = 0
    failed_to_log_count: int = 0

    def to_summary(self) -> dict[str, int]:
        return {
            "logged_count": self.logged_count,
            "failed_to_log_count": self.failed_to_log_count,
        }


class ToolExecutionAuditPreview(BaseModel):
    arguments_preview: dict[str, Any] = Field(default_factory=dict)
    result_preview: dict[str, Any] = Field(default_factory=dict)
    error_preview: dict[str, Any] | None = None


class ToolExecutionLogCreate(BaseModel):
    owner_id: UUID
    project_id: UUID
    task_id: UUID | None = None
    agent_id: UUID
    agent_run_id: UUID
    llm_request_id: UUID | None = None
    tool_call_id: str | None = None
    tool_name: str
    status: ToolExecutionLogStatus
    execution_mode: ToolExecutionLogMode
    reason: str | None = None
    arguments_preview: dict[str, Any] = Field(default_factory=dict)
    result_preview: dict[str, Any] = Field(default_factory=dict)
    error_payload: dict[str, Any] | None = None
    duration_ms: int | None = None


class ToolExecutionLogRead(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    task_id: UUID | None = None
    agent_id: UUID
    agent_run_id: UUID
    llm_request_id: UUID | None = None
    tool_call_id: str | None = None
    tool_name: str
    status: ToolExecutionLogStatus
    execution_mode: ToolExecutionLogMode
    reason: str | None = None
    arguments_preview: dict[str, Any] = Field(default_factory=dict)
    result_preview: dict[str, Any] = Field(default_factory=dict)
    error_payload: dict[str, Any] | None = None
    duration_ms: int | None = None
    created_at: datetime
