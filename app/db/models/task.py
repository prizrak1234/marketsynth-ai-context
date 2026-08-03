"""Task persistence model — mirrors app.schemas.contracts.Task."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import TaskStatus


class TaskTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "tasks"

    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    title: str = Field(max_length=512, nullable=False)
    status: TaskStatus = Field(default=TaskStatus.PENDING, nullable=False)
    input_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    output_payload: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    completed_at: datetime | None = Field(default=None)
