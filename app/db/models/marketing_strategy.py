"""MarketingStrategy persistence (Commercial MVP P0.6).

Commercial go-to-market strategy — not MarketingPlan / Campaign / execution.
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
    MarketingStrategyLifecycleStatus,
    MarketingStrategyOrigin,
    MarketingStrategyReadinessStatus,
    StrategyHandoffStatus,
    VerdictKind,
)


class MarketingStrategyTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_strategies"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_marketing_strategies_project_version"),
        Index("ix_marketing_strategies_owner_id", "owner_id"),
        Index("ix_marketing_strategies_project_id", "project_id"),
        Index("ix_marketing_strategies_business_verdict_id", "business_verdict_id"),
        Index("ix_marketing_strategies_lifecycle_status", "lifecycle_status"),
        Index("ix_marketing_strategies_readiness_status", "readiness_status"),
        Index("ix_marketing_strategies_version", "version"),
        Index("ix_marketing_strategies_supersedes_strategy_id", "supersedes_strategy_id"),
        Index("ix_marketing_strategies_project_id_version", "project_id", "version"),
        Index(
            "ix_marketing_strategies_project_id_lifecycle_status",
            "project_id",
            "lifecycle_status",
        ),
        Index("ix_marketing_strategies_strategy_origin", "strategy_origin"),
        Index("ix_marketing_strategies_created_at", "created_at"),
        Index("ix_marketing_strategies_approved_at", "approved_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    business_verdict_id: UUID = Field(foreign_key="business_verdicts.id", nullable=False)
    business_verdict_version: int = Field(nullable=False)
    business_verdict_type: VerdictKind = Field(nullable=False)
    evidence_snapshot_id: UUID = Field(
        foreign_key="business_verdict_evidence_snapshots.id",
        nullable=False,
    )
    evidence_snapshot_hash: str = Field(max_length=128, nullable=False)
    version: int = Field(nullable=False)
    lifecycle_status: MarketingStrategyLifecycleStatus = Field(
        default=MarketingStrategyLifecycleStatus.DRAFT,
        nullable=False,
    )
    strategy_origin: MarketingStrategyOrigin = Field(
        default=MarketingStrategyOrigin.MANUAL,
        nullable=False,
    )
    title: str = Field(max_length=240, nullable=False)
    executive_summary: str = Field(max_length=4000, nullable=False)
    primary_business_objective: str = Field(max_length=2000, nullable=False)
    strategic_horizon: str = Field(max_length=240, nullable=False)
    objectives: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    audience_segments: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    positioning: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    offers: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    channel_strategy: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    funnel: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    asset_plan: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    budget_policy: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    metrics: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    verdict_conditions: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    strategic_risks: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    assumptions: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    execution_constraints: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    readiness_status: MarketingStrategyReadinessStatus = Field(
        default=MarketingStrategyReadinessStatus.NOT_READY,
        nullable=False,
    )
    submitted_by: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    submitted_at: datetime | None = Field(default=None, nullable=True)
    approved_by: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    approved_at: datetime | None = Field(default=None, nullable=True)
    rejection_reason: str | None = Field(default=None, max_length=2000, nullable=True)
    supersedes_strategy_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_strategies.id",
        nullable=True,
    )
    related_marketing_plan_ids: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    handoff_status: StrategyHandoffStatus = Field(
        default=StrategyHandoffStatus.NOT_STARTED,
        nullable=False,
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
