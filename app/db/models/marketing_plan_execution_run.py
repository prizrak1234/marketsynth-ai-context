"""Marketing plan execution run persistence (Phase AI.29)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import MarketingPlanExecutionStatus


class MarketingPlanExecutionRunTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_plan_execution_runs"
    __table_args__ = (
        Index("ix_marketing_plan_execution_runs_owner_id", "owner_id"),
        Index("ix_marketing_plan_execution_runs_project_id", "project_id"),
        Index("ix_marketing_plan_execution_runs_marketing_plan_id", "marketing_plan_id"),
        Index("ix_marketing_plan_execution_runs_status", "status"),
        Index("ix_marketing_plan_execution_runs_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    marketing_plan_id: UUID = Field(foreign_key="marketing_plans.id", nullable=False)
    marketing_plan_version_number: int = Field(nullable=False)
    status: MarketingPlanExecutionStatus = Field(
        default=MarketingPlanExecutionStatus.QUEUED,
        nullable=False,
    )
    task_snapshots: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    result_summary: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    error: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    started_at: datetime | None = Field(default=None, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
