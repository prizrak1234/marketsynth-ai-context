"""Tool execution audit log persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now


class ToolExecutionLogTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "tool_execution_logs"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    task_id: UUID | None = Field(default=None, foreign_key="tasks.id", index=True)
    agent_id: UUID = Field(foreign_key="agents.id", index=True, nullable=False)
    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True, nullable=False)
    llm_request_id: UUID | None = Field(default=None, foreign_key="llm_requests.id", index=True)
    tool_call_id: str | None = Field(default=None, max_length=128)
    tool_name: str = Field(max_length=128, index=True, nullable=False)
    status: str = Field(max_length=32, index=True, nullable=False)
    execution_mode: str = Field(max_length=32, nullable=False)
    reason: str | None = Field(default=None, max_length=255)
    arguments_preview: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    result_preview: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    error_payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    duration_ms: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, index=True, nullable=False)
