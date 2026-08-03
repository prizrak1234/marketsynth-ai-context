"""Publishing foundation domain contracts (Phase AI.60–AI.65)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PublishingFoundationChannelType(StrEnum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    BLOG = "blog"


class PublishingFoundationChannelStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class PublicationPackageJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DRY_RUN_SUCCEEDED = "dry_run_succeeded"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublicationPackageJobScheduleStatus(StrEnum):
    UNSCHEDULED = "unscheduled"
    SCHEDULED = "scheduled"
    DUE = "due"
    DISPATCHED = "dispatched"
    CANCELLED = "cancelled"


class PublishingDispatchMode(StrEnum):
    DRY_RUN = "dry_run"
    REAL = "real"


class PublishingFoundationChannel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    channel_type: PublishingFoundationChannelType
    name: str
    status: PublishingFoundationChannelStatus = PublishingFoundationChannelStatus.DRAFT
    config_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PublicationPackageJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    publication_package_id: UUID
    channel_id: UUID
    status: PublicationPackageJobStatus = PublicationPackageJobStatus.QUEUED
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)
    snapshot_hash: str | None = None
    result_metadata: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
    replay_of_job_id: UUID | None = None
    scheduled_for: datetime | None = None
    schedule_status: PublicationPackageJobScheduleStatus = (
        PublicationPackageJobScheduleStatus.UNSCHEDULED
    )
    dispatch_attempts: int = 0
    last_dispatch_error: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DryRunPublishResult(BaseModel):
    result_metadata: dict[str, Any] = Field(default_factory=dict)


class PublishingAuditEventType(StrEnum):
    CHANNEL_CREATED = "publishing.channel.created"
    CHANNEL_ARCHIVED = "publishing.channel.archived"
    JOB_CREATED = "publishing.job.created"
    JOB_STARTED = "publishing.job.started"
    JOB_DRY_RUN_SUCCEEDED = "publishing.job.dry_run_succeeded"
    JOB_FAILED = "publishing.job.failed"
    JOB_REPLAYED = "publishing.job.replayed"
    JOB_REAL_EXECUTE_REQUESTED = "publishing.job.real_execute_requested"
    JOB_SUCCEEDED = "publishing.job.succeeded"
    JOB_SCHEDULED = "publishing.job.scheduled"
    JOB_UNSCHEDULED = "publishing.job.unscheduled"
    JOB_MARKED_DUE = "publishing.job.marked_due"
    JOB_DISPATCH_REQUESTED = "publishing.job.dispatch_requested"
    JOB_DISPATCHED = "publishing.job.dispatched"
    JOB_DISPATCH_FAILED = "publishing.job.dispatch_failed"


class PublishingFoundationMetrics(BaseModel):
    jobs_total: int = 0
    jobs_by_status: dict[str, int] = Field(default_factory=dict)
    jobs_by_channel_type: dict[str, int] = Field(default_factory=dict)
    latest_activity_at: datetime | None = None
    real_jobs_total: int = 0
    real_jobs_succeeded: int = 0
    real_jobs_failed: int = 0
    jobs_by_provider: dict[str, int] = Field(default_factory=dict)
    scheduled_jobs_total: int = 0
    due_jobs_total: int = 0
    dispatched_jobs_total: int = 0
    dispatch_failed_total: int = 0
    scheduled_jobs_by_channel_type: dict[str, int] = Field(default_factory=dict)
