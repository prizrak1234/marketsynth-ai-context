"""Publication delivery attempt audit log (Phase 6.1)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.publishing.contracts import (
    PublicationDeliveryLogStatus,
    PublishingChannelType,
)


class PublicationDeliveryLogTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "publication_delivery_logs"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    publication_job_id: UUID = Field(
        foreign_key="publication_jobs.id",
        index=True,
        nullable=False,
    )
    channel_id: UUID = Field(foreign_key="publishing_channels.id", index=True, nullable=False)
    channel_type: PublishingChannelType = Field(max_length=32, index=True, nullable=False)
    status: PublicationDeliveryLogStatus = Field(max_length=32, index=True, nullable=False)
    attempt_number: int = Field(default=1, nullable=False)
    duration_ms: int | None = Field(default=None)
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=512)
    response_preview: str | None = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=utc_now, index=True, nullable=False)
