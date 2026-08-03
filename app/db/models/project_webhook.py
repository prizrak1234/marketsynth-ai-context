"""Project outbound webhook subscriptions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class ProjectWebhookTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "project_webhooks"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    url: str = Field(max_length=2048, nullable=False)
    signing_secret: str = Field(max_length=255, nullable=False)
    subscribed_event_types: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    is_active: bool = Field(default=True, index=True, nullable=False)
