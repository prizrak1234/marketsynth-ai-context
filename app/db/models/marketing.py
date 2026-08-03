"""Marketing domain persistence — briefs and content assets (Phase 4.0)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.marketing.contracts import (
    ContentAssetStatus,
    ContentAssetType,
    ContentAssetVersionSource,
    MarketingBriefStatus,
    PublicationPackageChannel,
    PublicationPackageStatus,
)


class MarketingBriefTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_briefs"
    __table_args__ = (
        Index("ix_marketing_briefs_owner_id", "owner_id"),
        Index("ix_marketing_briefs_project_id", "project_id"),
        Index("ix_marketing_briefs_status", "status"),
        Index("ix_marketing_briefs_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    title: str = Field(max_length=512, nullable=False)
    product_description: str = Field(default="", nullable=False)
    target_audience: str = Field(default="", nullable=False)
    offer: str = Field(default="", nullable=False)
    goals: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: MarketingBriefStatus = Field(
        default=MarketingBriefStatus.DRAFT,
        nullable=False,
    )


class ContentAssetTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "content_assets"
    __table_args__ = (
        Index("ix_content_assets_owner_id", "owner_id"),
        Index("ix_content_assets_project_id", "project_id"),
        Index("ix_content_assets_brief_id", "brief_id"),
        Index("ix_content_assets_campaign_id", "campaign_id"),
        Index("ix_content_assets_task_id", "task_id"),
        Index("ix_content_assets_agent_run_id", "agent_run_id"),
        Index("ix_content_assets_asset_type", "asset_type"),
        Index("ix_content_assets_status", "status"),
        Index("ix_content_assets_created_at", "created_at"),
        Index("ix_content_assets_source_asset_id", "source_asset_id"),
        Index(
            "ix_content_assets_source_asset_revision",
            "source_asset_id",
            "revision_number",
        ),
        Index(
            "ix_content_assets_source_specialist_output_id",
            "source_specialist_output_id",
        ),
        Index("ix_content_assets_source_execution_run_id", "source_execution_run_id"),
        Index("ix_content_assets_source_marketing_plan_id", "source_marketing_plan_id"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    brief_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_briefs.id",
        nullable=True,
    )
    campaign_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_campaigns.id",
        nullable=True,
    )
    task_id: UUID | None = Field(default=None, foreign_key="tasks.id", nullable=True)
    agent_run_id: UUID | None = Field(
        default=None,
        foreign_key="agent_runs.id",
        nullable=True,
    )
    asset_type: ContentAssetType = Field(nullable=False)
    title: str = Field(max_length=512, nullable=False)
    body: str = Field(default="", nullable=False)
    asset_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    status: ContentAssetStatus = Field(
        default=ContentAssetStatus.DRAFT,
        nullable=False,
    )
    current_version_number: int = Field(default=1, nullable=False)
    approved_version_number: int | None = Field(default=None, nullable=True)
    source_asset_id: UUID | None = Field(
        default=None,
        foreign_key="content_assets.id",
        nullable=True,
    )
    source_version_number: int | None = Field(default=None, nullable=True)
    revision_number: int | None = Field(default=None, nullable=True)
    source_marketing_plan_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_plans.id",
        nullable=True,
    )
    source_execution_run_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_plan_execution_runs.id",
        nullable=True,
    )
    source_specialist_output_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_specialist_outputs.id",
        nullable=True,
    )
    source_specialist_type: str | None = Field(default=None, max_length=32, nullable=True)
    submitted_for_review_at: datetime | None = Field(default=None, nullable=True)
    approved_at: datetime | None = Field(default=None, nullable=True)


class PublicationPackageTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "publication_packages"
    __table_args__ = (
        Index("ix_publication_packages_owner_id", "owner_id"),
        Index("ix_publication_packages_project_id", "project_id"),
        Index("ix_publication_packages_content_asset_id", "content_asset_id"),
        Index("ix_publication_packages_source_content_asset_id", "source_content_asset_id"),
        Index("ix_publication_packages_status", "status"),
        Index(
            "uq_publication_packages_asset_channel",
            "content_asset_id",
            "channel",
            unique=True,
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    content_asset_id: UUID = Field(foreign_key="content_assets.id", nullable=False)
    source_content_asset_id: UUID = Field(foreign_key="content_assets.id", nullable=False)
    channel: PublicationPackageChannel = Field(nullable=False)
    title: str = Field(max_length=512, nullable=False)
    body: str = Field(default="", nullable=False)
    cta: str | None = Field(default=None, max_length=512, nullable=True)
    package_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    status: PublicationPackageStatus = Field(
        default=PublicationPackageStatus.DRAFT,
        nullable=False,
    )
    submitted_for_review_at: datetime | None = Field(default=None, nullable=True)
    approved_at: datetime | None = Field(default=None, nullable=True)


class ContentAssetVersionTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "content_asset_versions"
    __table_args__ = (
        Index("ix_content_asset_versions_owner_project", "owner_id", "project_id"),
        Index("ix_content_asset_versions_asset_id", "asset_id"),
        Index(
            "uq_content_asset_versions_asset_version",
            "asset_id",
            "version_number",
            unique=True,
        ),
        Index("ix_content_asset_versions_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    asset_id: UUID = Field(foreign_key="content_assets.id", nullable=False)
    version_number: int = Field(nullable=False)
    title: str = Field(max_length=512, nullable=False)
    body: str = Field(default="", nullable=False)
    version_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    created_by_source: ContentAssetVersionSource = Field(nullable=False)
    created_by_agent_run_id: UUID | None = Field(
        default=None,
        foreign_key="agent_runs.id",
        nullable=True,
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
    )
