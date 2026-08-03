"""Agent tool contracts — definitions, calls, and results (no execution)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.contracts import AgentType
from app.tools.audit_contracts import ToolAuditTracker

ToolName = str


class ToolParameterSchema(BaseModel):
    name: str
    description: str | None = None
    json_schema: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    name: ToolName
    description: str
    parameters_schema: dict[str, Any]
    enabled: bool = True
    allowed_agent_types: list[AgentType] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    id: str | None = None
    name: ToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    raw_arguments: dict[str, Any] | str | None = None


class ToolResult(BaseModel):
    call_id: str | None = None
    name: ToolName
    status: Literal["succeeded", "failed", "skipped"]
    output: dict[str, Any] | str | None = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionContext(BaseModel):
    owner_id: UUID
    project_id: UUID
    agent_id: UUID
    agent_type: AgentType
    agent_run_id: UUID
    task_id: UUID | None = None
    request_id: UUID | None = None
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    audit_tracker: ToolAuditTracker | None = None
