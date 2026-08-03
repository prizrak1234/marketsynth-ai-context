"""Media production persistence (Phase AI.50–AI.54)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.marketing.media_contracts import (
    MediaAssetStatus,
    MediaAssetType,
    MediaBriefStatus,
)
from app.media_generation.contracts import (
    MediaGenerationJobStatus,
    MediaGenerationProvider,
)


class MediaBriefTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "media_briefs"
    __table_args__ = (
        Index("ix_media_briefs_owner_id", "owner_id"),
        Index("ix_media_briefs_project_id", "project_id"),
        Index("ix_media_briefs_content_asset_id", "content_asset_id"),
        Index("ix_media_briefs_source_content_asset_id", "source_content_asset_id"),
        Index("ix_media_briefs_status", "status"),
        Index("uq_media_briefs_content_asset_id", "content_asset_id", unique=True),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    content_asset_id: UUID = Field(foreign_key="content_assets.id", nullable=False)
    source_content_asset_id: UUID = Field(foreign_key="content_assets.id", nullable=False)
    status: MediaBriefStatus = Field(default=MediaBriefStatus.DRAFT, nullable=False)
    title: str = Field(max_length=512, nullable=False)
    goal: str = Field(default="", nullable=False)
    target_audience: str = Field(default="", nullable=False)
    platform: str = Field(default="", max_length=128, nullable=False)
    creative_direction: str = Field(default="", nullable=False)
    visual_style: str = Field(default="", nullable=False)
    composition: str = Field(default="", nullable=False)
    text_overlay: str = Field(default="", nullable=False)
    references: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    submitted_for_review_at: datetime | None = Field(default=None, nullable=True)
    approved_at: datetime | None = Field(default=None, nullable=True)


class MediaAssetTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "media_assets"
    __table_args__ = (
        Index("ix_media_assets_owner_id", "owner_id"),
        Index("ix_media_assets_project_id", "project_id"),
        Index("ix_media_assets_media_brief_id", "media_brief_id"),
        Index("ix_media_assets_source_media_brief_id", "source_media_brief_id"),
        Index("ix_media_assets_status", "status"),
        Index("ix_media_assets_media_type", "media_type"),
        Index(
            "uq_media_assets_brief_type",
            "media_brief_id",
            "media_type",
            unique=True,
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    media_brief_id: UUID = Field(foreign_key="media_briefs.id", nullable=False)
    source_media_brief_id: UUID = Field(foreign_key="media_briefs.id", nullable=False)
    media_type: MediaAssetType = Field(nullable=False)
    status: MediaAssetStatus = Field(default=MediaAssetStatus.DRAFT, nullable=False)
    generation_provider: str | None = Field(default=None, max_length=64, nullable=True)
    generation_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    source_generation_job_id: UUID | None = Field(
        default=None,
        foreign_key="media_generation_jobs.id",
        nullable=True,
    )
    provider: str | None = Field(default=None, max_length=64, nullable=True)
    provider_asset_ref: str | None = Field(default=None, max_length=512, nullable=True)
    storage_uri: str | None = Field(default=None, max_length=512, nullable=True)
    mime_type: str | None = Field(default=None, max_length=64, nullable=True)
    width: int | None = Field(default=None, nullable=True)
    height: int | None = Field(default=None, nullable=True)
    current_version_number: int = Field(default=1, nullable=False)


class MediaAssetVersionTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "media_asset_versions"
    __table_args__ = (
        Index("ix_media_asset_versions_media_asset_id", "media_asset_id"),
        Index(
            "uq_media_asset_versions_asset_version",
            "media_asset_id",
            "version_number",
            unique=True,
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    media_asset_id: UUID = Field(foreign_key="media_assets.id", nullable=False)
    version_number: int = Field(nullable=False)
    source_generation_job_id: UUID | None = Field(
        default=None,
        foreign_key="media_generation_jobs.id",
        nullable=True,
    )
    storage_uri: str | None = Field(default=None, max_length=512, nullable=True)
    provider_asset_ref: str | None = Field(default=None, max_length=512, nullable=True)
    version_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class MediaGenerationJobTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "media_generation_jobs"
    __table_args__ = (
        Index("ix_media_generation_jobs_owner_id", "owner_id"),
        Index("ix_media_generation_jobs_project_id", "project_id"),
        Index("ix_media_generation_jobs_media_brief_id", "media_brief_id"),
        Index("ix_media_generation_jobs_media_asset_id", "media_asset_id"),
        Index("ix_media_generation_jobs_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    media_brief_id: UUID = Field(foreign_key="media_briefs.id", nullable=False)
    media_asset_id: UUID | None = Field(
        default=None,
        foreign_key="media_assets.id",
        nullable=True,
    )
    provider: MediaGenerationProvider = Field(nullable=False)
    media_type: str = Field(max_length=32, nullable=False)
    prompt: str = Field(default="", nullable=False)
    status: MediaGenerationJobStatus = Field(
        default=MediaGenerationJobStatus.QUEUED,
        nullable=False,
    )
    result_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    error: str | None = Field(default=None, max_length=1024, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    started_at: datetime | None = Field(default=None, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
