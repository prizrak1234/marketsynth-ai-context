"""Publishing domain contracts — channels and publication jobs (Phase 6.0)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PublishingChannelType(StrEnum):
    WEBHOOK = "webhook"
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    BLOG = "blog"
    EMAIL = "email"
    TILDA = "tilda"
    CUSTOM = "custom"


class PublishingChannelStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class PublicationJobStatus(StrEnum):
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublicationDeliveryLogStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class PublishingChannel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    name: str
    type: PublishingChannelType
    status: PublishingChannelStatus = PublishingChannelStatus.ACTIVE
    config_preview: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PublicationJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    asset_id: UUID
    asset_version_number: int
    channel_id: UUID
    campaign_id: UUID | None = None
    status: PublicationJobStatus = PublicationJobStatus.QUEUED
    attempts: int = 0
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: datetime | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PublicationDeliveryLog(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    publication_job_id: UUID
    channel_id: UUID
    channel_type: PublishingChannelType
    status: PublicationDeliveryLogStatus
    attempt_number: int
    duration_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    response_preview: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
