"""Agent run persistence model — mirrors app.schemas.contracts.AgentRun."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import AgentRunStatus


class AgentRunTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "agent_runs"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    task_id: UUID | None = Field(default=None, foreign_key="tasks.id", index=True)
    agent_id: UUID = Field(foreign_key="agents.id", index=True, nullable=False)
    parent_agent_run_id: UUID | None = Field(
        default=None,
        foreign_key="agent_runs.id",
        index=True,
    )
    status: AgentRunStatus = Field(default=AgentRunStatus.QUEUED, index=True, nullable=False)
    input_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    output_payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    error: str | None = Field(default=None)
    run_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
