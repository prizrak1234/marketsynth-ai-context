"""Event outbox persistence — internal notifications before webhooks."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import EventOutboxStatus, EventType


class EventOutboxTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "event_outbox"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    event_type: EventType = Field(index=True, nullable=False)
    aggregate_type: str = Field(max_length=64, index=True, nullable=False)
    aggregate_id: UUID = Field(index=True, nullable=False)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: EventOutboxStatus = Field(
        default=EventOutboxStatus.PENDING,
        index=True,
        nullable=False,
    )
    attempts: int = Field(default=0, nullable=False)
    last_error: str | None = Field(default=None)
