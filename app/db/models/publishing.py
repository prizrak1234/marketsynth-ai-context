"""Publishing layer persistence — channels and publication jobs (Phase 6.0)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, Text
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.publishing.contracts import (
    PublicationJobStatus,
    PublishingChannelStatus,
    PublishingChannelType,
)


class PublishingChannelTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "publishing_channels"
    __table_args__ = (
        Index("ix_publishing_channels_owner_id", "owner_id"),
        Index("ix_publishing_channels_project_id", "project_id"),
        Index("ix_publishing_channels_type", "channel_type"),
        Index("ix_publishing_channels_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    name: str = Field(max_length=256, nullable=False)
    channel_type: PublishingChannelType = Field(nullable=False)
    status: PublishingChannelStatus = Field(
        default=PublishingChannelStatus.ACTIVE,
        nullable=False,
    )
    channel_config: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    config_preview: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class PublicationJobTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "publication_jobs"
    __table_args__ = (
        Index("ix_publication_jobs_owner_id", "owner_id"),
        Index("ix_publication_jobs_project_id", "project_id"),
        Index("ix_publication_jobs_asset_id", "asset_id"),
        Index("ix_publication_jobs_channel_id", "channel_id"),
        Index("ix_publication_jobs_campaign_id", "campaign_id"),
        Index("ix_publication_jobs_status", "status"),
        Index("ix_publication_jobs_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    asset_id: UUID = Field(foreign_key="content_assets.id", nullable=False)
    asset_version_number: int = Field(nullable=False)
    channel_id: UUID = Field(foreign_key="publishing_channels.id", nullable=False)
    campaign_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_campaigns.id",
        nullable=True,
    )
    status: PublicationJobStatus = Field(
        default=PublicationJobStatus.QUEUED,
        nullable=False,
    )
    attempts: int = Field(default=0, nullable=False)
    payload_preview: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    scheduled_at: datetime | None = Field(default=None, nullable=True)
    queued_at: datetime | None = Field(default=None, nullable=True)
    started_at: datetime | None = Field(default=None, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
