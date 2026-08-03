"""Marketing specialist output artifacts (Phase AI.30)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import MarketingSpecialistOutputStatus, MarketingSpecialistType


class MarketingSpecialistOutputTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_specialist_outputs"
    __table_args__ = (
        UniqueConstraint(
            "execution_run_id",
            "task_index",
            name="uq_marketing_specialist_outputs_run_task",
        ),
        Index("ix_marketing_specialist_outputs_owner_id", "owner_id"),
        Index("ix_marketing_specialist_outputs_project_id", "project_id"),
        Index("ix_marketing_specialist_outputs_marketing_plan_id", "marketing_plan_id"),
        Index("ix_marketing_specialist_outputs_execution_run_id", "execution_run_id"),
        Index("ix_marketing_specialist_outputs_specialist", "specialist"),
        Index("ix_marketing_specialist_outputs_status", "status"),
        Index("ix_marketing_specialist_outputs_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    marketing_plan_id: UUID = Field(foreign_key="marketing_plans.id", nullable=False)
    execution_run_id: UUID = Field(
        foreign_key="marketing_plan_execution_runs.id",
        nullable=False,
    )
    task_index: int = Field(nullable=False)
    specialist: MarketingSpecialistType = Field(nullable=False)
    title: str = Field(max_length=512, nullable=False)
    output_type: str = Field(max_length=64, nullable=False, default="placeholder")
    content: str = Field(max_length=8192, nullable=False)
    structured_data: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    status: MarketingSpecialistOutputStatus = Field(
        default=MarketingSpecialistOutputStatus.DRAFT,
        nullable=False,
    )
    current_version_number: int = Field(default=1, nullable=False)
    approved_version_number: int | None = Field(default=None, nullable=True)


class MarketingSpecialistOutputVersionTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "marketing_specialist_output_versions"
    __table_args__ = (
        UniqueConstraint(
            "specialist_output_id",
            "version_number",
            name="uq_marketing_specialist_output_versions_output_version",
        ),
        Index(
            "ix_marketing_specialist_output_versions_specialist_output_id",
            "specialist_output_id",
        ),
        Index("ix_marketing_specialist_output_versions_created_at", "created_at"),
    )

    specialist_output_id: UUID = Field(
        foreign_key="marketing_specialist_outputs.id",
        nullable=False,
    )
    version_number: int = Field(nullable=False)
    title: str = Field(max_length=512, nullable=False)
    output_type: str = Field(max_length=64, nullable=False)
    content: str = Field(max_length=8192, nullable=False)
    structured_data: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_by_run_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_plan_execution_runs.id",
        nullable=True,
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
