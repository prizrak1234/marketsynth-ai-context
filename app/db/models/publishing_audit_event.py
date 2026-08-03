"""Publishing audit events — safe metadata only (Phase AI.64)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.publishing_foundation.contracts import PublishingAuditEventType


class PublishingAuditEventTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "publishing_audit_events"
    __table_args__ = (
        Index("ix_publishing_audit_events_owner_id", "owner_id"),
        Index("ix_publishing_audit_events_project_id", "project_id"),
        Index("ix_publishing_audit_events_event_type", "event_type"),
        Index("ix_publishing_audit_events_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    event_type: PublishingAuditEventType = Field(nullable=False)
    status: str = Field(max_length=32, nullable=False)
    channel_id: UUID | None = Field(
        default=None,
        foreign_key="publishing_channels.id",
        nullable=True,
    )
    publication_package_job_id: UUID | None = Field(
        default=None,
        foreign_key="publication_package_jobs.id",
        nullable=True,
    )
    safe_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
