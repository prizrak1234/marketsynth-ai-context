"""Chat audit events (Phase AI.25) — safe operational visibility only."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    ChatAuditEventType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
)


class ChatAuditEventTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "chat_audit_events"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    session_id: UUID | None = Field(
        default=None,
        foreign_key="agent_chat_sessions.id",
        index=True,
    )
    message_id: UUID | None = Field(default=None, index=True)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", index=True)
    event_type: ChatAuditEventType = Field(max_length=64, index=True, nullable=False)
    domain: ChatSessionDomain = Field(max_length=32, nullable=False)
    entrypoint: ChatSessionEntrypoint = Field(max_length=32, nullable=False)
    status: str = Field(max_length=32, index=True, nullable=False)
    safe_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True, nullable=False)
