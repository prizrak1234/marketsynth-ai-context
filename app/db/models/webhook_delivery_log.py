"""Webhook delivery attempt audit log."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import WebhookDeliveryLogStatus


class WebhookDeliveryLogTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "webhook_delivery_logs"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    webhook_id: UUID | None = Field(default=None, foreign_key="project_webhooks.id", index=True)
    event_outbox_id: UUID = Field(foreign_key="event_outbox.id", index=True, nullable=False)
    event_type: str = Field(max_length=128, index=True, nullable=False)
    target_url_preview: str = Field(max_length=512, nullable=False)
    status: WebhookDeliveryLogStatus = Field(max_length=32, index=True, nullable=False)
    http_status_code: int | None = Field(default=None)
    attempt_number: int = Field(default=1, nullable=False)
    duration_ms: int | None = Field(default=None)
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=512)
    response_preview: str | None = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=utc_now, index=True, nullable=False)
