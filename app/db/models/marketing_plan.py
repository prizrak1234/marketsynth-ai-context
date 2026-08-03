"""Marketing plan persistence (Phase AI.28)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import MarketingExecutionMode, MarketingPlanStatus


class MarketingPlanTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_plans"
    __table_args__ = (
        Index("ix_marketing_plans_owner_id", "owner_id"),
        Index("ix_marketing_plans_project_id", "project_id"),
        Index("ix_marketing_plans_status", "status"),
        Index("ix_marketing_plans_source_run_id", "source_run_id"),
        Index("ix_marketing_plans_source_session_id", "source_session_id"),
        Index("ix_marketing_plans_source_scenario_id", "source_scenario_id"),
        Index("ix_marketing_plans_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    source_run_id: UUID | None = Field(
        default=None,
        foreign_key="agent_runs.id",
        nullable=True,
    )
    source_session_id: UUID | None = Field(
        default=None,
        foreign_key="agent_chat_sessions.id",
        nullable=True,
    )
    source_scenario_id: str | None = Field(default=None, max_length=128, nullable=True)
    source_scenario_name: str | None = Field(default=None, max_length=256, nullable=True)
    title: str = Field(max_length=512, nullable=False)
    goal: str = Field(max_length=4096, nullable=False)
    project_context: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    specialist_tasks: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    execution_mode: MarketingExecutionMode = Field(
        default=MarketingExecutionMode.PLANNING,
        nullable=False,
    )
    status: MarketingPlanStatus = Field(
        default=MarketingPlanStatus.DRAFT,
        nullable=False,
    )
    current_version_number: int = Field(default=1, nullable=False)
    approved_version_number: int | None = Field(default=None, nullable=True)


class MarketingPlanVersionTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "marketing_plan_versions"
    __table_args__ = (
        UniqueConstraint(
            "marketing_plan_id",
            "version_number",
            name="uq_marketing_plan_versions_plan_version",
        ),
        Index("ix_marketing_plan_versions_marketing_plan_id", "marketing_plan_id"),
        Index("ix_marketing_plan_versions_created_at", "created_at"),
    )

    marketing_plan_id: UUID = Field(foreign_key="marketing_plans.id", nullable=False)
    version_number: int = Field(nullable=False)
    goal: str = Field(max_length=4096, nullable=False)
    project_context: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    specialist_tasks: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    execution_mode: MarketingExecutionMode = Field(
        default=MarketingExecutionMode.PLANNING,
        nullable=False,
    )
    created_by_run_id: UUID | None = Field(
        default=None,
        foreign_key="agent_runs.id",
        nullable=True,
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
