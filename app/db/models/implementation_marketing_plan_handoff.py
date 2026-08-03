"""Implementation → MarketingPlan handoff snapshot (Commercial MVP P1.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import ImplementationMarketingPlanHandoffStatus


class ImplementationMarketingPlanHandoffTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "implementation_marketing_plan_handoffs"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "mapping_fingerprint",
            name="uq_impl_mp_handoffs_project_fingerprint",
        ),
        Index("ix_impl_mp_handoffs_owner_id", "owner_id"),
        Index("ix_impl_mp_handoffs_project_id", "project_id"),
        Index("ix_impl_mp_handoffs_implementation_plan_id", "implementation_plan_id"),
        Index("ix_impl_mp_handoffs_marketing_plan_id", "marketing_plan_id"),
        Index("ix_impl_mp_handoffs_lifecycle_status", "lifecycle_status"),
        Index("ix_impl_mp_handoffs_mapping_fingerprint", "mapping_fingerprint"),
        Index(
            "ix_impl_mp_handoffs_plan_id_version",
            "implementation_plan_id",
            "implementation_plan_version",
        ),
        Index(
            "ix_impl_mp_handoffs_project_fingerprint",
            "project_id",
            "mapping_fingerprint",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    implementation_plan_id: UUID = Field(
        foreign_key="implementation_plans.id", nullable=False
    )
    implementation_plan_version: int = Field(nullable=False)
    marketing_strategy_id: UUID = Field(
        foreign_key="marketing_strategies.id", nullable=False
    )
    business_verdict_id: UUID = Field(foreign_key="business_verdicts.id", nullable=False)
    source_snapshot_hash: str = Field(max_length=128, nullable=False)
    mapping_version: str = Field(max_length=64, nullable=False)
    mapping_fingerprint: str = Field(max_length=128, nullable=False)
    lifecycle_status: ImplementationMarketingPlanHandoffStatus = Field(
        default=ImplementationMarketingPlanHandoffStatus.PREVIEW,
        nullable=False,
    )
    preview_payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    included_task_count: int = Field(default=0, nullable=False)
    excluded_task_count: int = Field(default=0, nullable=False)
    blocked_task_count: int = Field(default=0, nullable=False)
    warnings: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    confirmed_by: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    confirmed_at: datetime | None = Field(default=None, nullable=True)
    marketing_plan_id: UUID | None = Field(
        default=None, foreign_key="marketing_plans.id", nullable=True
    )
    marketing_plan_version: int | None = Field(default=None, nullable=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
