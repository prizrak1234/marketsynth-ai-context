"""ImplementationPlan persistence (Commercial MVP P1.1).

Project delivery plan linked to approved MarketingStrategy — not MarketingPlan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import (
    ImplementationPlanLifecycleStatus,
    ImplementationPlanOrigin,
    ImplementationPlanReadinessStatus,
)


class ImplementationPlanTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "implementation_plans"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_implementation_plans_project_version"),
        Index("ix_implementation_plans_owner_id", "owner_id"),
        Index("ix_implementation_plans_project_id", "project_id"),
        Index("ix_implementation_plans_marketing_strategy_id", "marketing_strategy_id"),
        Index("ix_implementation_plans_lifecycle_status", "lifecycle_status"),
        Index("ix_implementation_plans_readiness_status", "readiness_status"),
        Index("ix_implementation_plans_version", "version"),
        Index("ix_implementation_plans_supersedes_plan_id", "supersedes_plan_id"),
        Index("ix_implementation_plans_project_id_version", "project_id", "version"),
        Index(
            "ix_implementation_plans_project_id_lifecycle_status",
            "project_id",
            "lifecycle_status",
        ),
        Index("ix_implementation_plans_plan_origin", "plan_origin"),
        Index("ix_implementation_plans_created_at", "created_at"),
        Index("ix_implementation_plans_approved_at", "approved_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    marketing_strategy_id: UUID = Field(foreign_key="marketing_strategies.id", nullable=False)
    marketing_strategy_version: int = Field(nullable=False)
    business_verdict_id: UUID = Field(foreign_key="business_verdicts.id", nullable=False)
    business_verdict_version: int = Field(nullable=False)
    evidence_snapshot_id: UUID = Field(
        foreign_key="business_verdict_evidence_snapshots.id",
        nullable=False,
    )
    evidence_snapshot_hash: str = Field(max_length=128, nullable=False)
    version: int = Field(nullable=False)
    lifecycle_status: ImplementationPlanLifecycleStatus = Field(
        default=ImplementationPlanLifecycleStatus.DRAFT,
        nullable=False,
    )
    plan_origin: ImplementationPlanOrigin = Field(
        default=ImplementationPlanOrigin.MANUAL,
        nullable=False,
    )
    title: str = Field(max_length=240, nullable=False)
    summary: str = Field(max_length=4000, nullable=False)
    implementation_horizon: str = Field(max_length=240, nullable=False)
    workstreams: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    milestones: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    tasks: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    role_assignments: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    dependencies: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    deliverables: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    budget_plan: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    budget_gates: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    approval_gates: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    conditions: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    implementation_risks: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    assumptions: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    roadmap: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    readiness_status: ImplementationPlanReadinessStatus = Field(
        default=ImplementationPlanReadinessStatus.NOT_READY,
        nullable=False,
    )
    readiness_reasons: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    submitted_by: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    submitted_at: datetime | None = Field(default=None, nullable=True)
    approved_by: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    approved_at: datetime | None = Field(default=None, nullable=True)
    rejection_reason: str | None = Field(default=None, max_length=2000, nullable=True)
    block_reason: str | None = Field(default=None, max_length=2000, nullable=True)
    supersedes_plan_id: UUID | None = Field(
        default=None,
        foreign_key="implementation_plans.id",
        nullable=True,
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
