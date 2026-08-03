"""Marketing funnel persistence (Phase 4.8)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.marketing.funnel_contracts import (
    FunnelStepAssetRole,
    FunnelStepStatus,
    FunnelStepType,
    MarketingFunnelStatus,
)


class MarketingFunnelTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_funnels"
    __table_args__ = (
        Index("ix_marketing_funnels_owner_id", "owner_id"),
        Index("ix_marketing_funnels_project_id", "project_id"),
        Index("ix_marketing_funnels_brief_id", "brief_id"),
        Index("ix_marketing_funnels_status", "status"),
        Index("ix_marketing_funnels_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    brief_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_briefs.id",
        nullable=True,
    )
    title: str = Field(max_length=512, nullable=False)
    description: str = Field(default="", nullable=False)
    funnel_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    status: MarketingFunnelStatus = Field(
        default=MarketingFunnelStatus.DRAFT,
        nullable=False,
    )


class MarketingFunnelStepTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_funnel_steps"
    __table_args__ = (
        Index("ix_marketing_funnel_steps_owner_id", "owner_id"),
        Index("ix_marketing_funnel_steps_project_id", "project_id"),
        Index("ix_marketing_funnel_steps_funnel_id", "funnel_id"),
        Index("ix_marketing_funnel_steps_step_type", "step_type"),
        Index("ix_marketing_funnel_steps_position", "position"),
        Index("ix_marketing_funnel_steps_status", "status"),
        UniqueConstraint("funnel_id", "position", name="uq_marketing_funnel_steps_funnel_position"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    funnel_id: UUID = Field(foreign_key="marketing_funnels.id", nullable=False)
    step_type: FunnelStepType = Field(nullable=False)
    title: str = Field(max_length=512, nullable=False)
    description: str = Field(default="", nullable=False)
    position: int = Field(nullable=False)
    step_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    status: FunnelStepStatus = Field(
        default=FunnelStepStatus.DRAFT,
        nullable=False,
    )


class FunnelStepAssetLinkTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "funnel_step_asset_links"
    __table_args__ = (
        Index("ix_funnel_step_asset_links_owner_id", "owner_id"),
        Index("ix_funnel_step_asset_links_project_id", "project_id"),
        Index("ix_funnel_step_asset_links_funnel_id", "funnel_id"),
        Index("ix_funnel_step_asset_links_step_id", "step_id"),
        Index("ix_funnel_step_asset_links_asset_id", "asset_id"),
        Index("ix_funnel_step_asset_links_role", "role"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    funnel_id: UUID = Field(foreign_key="marketing_funnels.id", nullable=False)
    step_id: UUID = Field(foreign_key="marketing_funnel_steps.id", nullable=False)
    asset_id: UUID = Field(foreign_key="content_assets.id", nullable=False)
    role: FunnelStepAssetRole = Field(
        default=FunnelStepAssetRole.PRIMARY,
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
    )
