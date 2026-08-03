"""Publication package jobs — dry-run publishing foundation (Phase AI.62)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
)


class PublicationPackageJobTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "publication_package_jobs"
    __table_args__ = (
        Index("ix_publication_package_jobs_owner_id", "owner_id"),
        Index("ix_publication_package_jobs_project_id", "project_id"),
        Index(
            "ix_publication_package_jobs_publication_package_id",
            "publication_package_id",
        ),
        Index("ix_publication_package_jobs_channel_id", "channel_id"),
        Index("ix_publication_package_jobs_status", "status"),
        Index("ix_publication_package_jobs_created_at", "created_at"),
        Index(
            "ix_publication_package_jobs_idempotency_key_hash",
            "owner_id",
            "project_id",
            "idempotency_key_hash",
        ),
        Index("ix_publication_package_jobs_replay_of_job_id", "replay_of_job_id"),
        Index("ix_publication_package_jobs_schedule_status", "schedule_status"),
        Index("ix_publication_package_jobs_scheduled_for", "scheduled_for"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    publication_package_id: UUID = Field(
        foreign_key="publication_packages.id",
        nullable=False,
    )
    channel_id: UUID = Field(foreign_key="publishing_channels.id", nullable=False)
    status: PublicationPackageJobStatus = Field(
        default=PublicationPackageJobStatus.QUEUED,
        nullable=False,
    )
    payload_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    result_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    error: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    snapshot_hash: str | None = Field(default=None, max_length=64, nullable=True)
    idempotency_key_hash: str | None = Field(default=None, max_length=64, nullable=True)
    idempotency_fingerprint: str | None = Field(default=None, max_length=64, nullable=True)
    replay_of_job_id: UUID | None = Field(
        default=None,
        foreign_key="publication_package_jobs.id",
        nullable=True,
    )
    scheduled_for: datetime | None = Field(default=None, nullable=True)
    schedule_status: PublicationPackageJobScheduleStatus = Field(
        default=PublicationPackageJobScheduleStatus.UNSCHEDULED,
        nullable=False,
    )
    dispatch_attempts: int = Field(default=0, nullable=False)
    last_dispatch_error: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    started_at: datetime | None = Field(default=None, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
