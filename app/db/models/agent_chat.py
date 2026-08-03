"""Agent chat session and message persistence (Phase AI.1, AI.19)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    AgentChatMessageRole,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionStatus,
)


class AgentChatSessionTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "agent_chat_sessions"
    __table_args__ = (
        Index("ix_agent_chat_sessions_owner_id", "owner_id"),
        Index("ix_agent_chat_sessions_project_id", "project_id"),
        Index("ix_agent_chat_sessions_agent_id", "agent_id"),
        Index("ix_agent_chat_sessions_status", "status"),
        Index("ix_agent_chat_sessions_updated_at", "updated_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    agent_id: UUID | None = Field(default=None, foreign_key="agents.id", nullable=True)
    entrypoint: ChatSessionEntrypoint = Field(
        default=ChatSessionEntrypoint.DIRECT_SPECIALIST,
        max_length=32,
        nullable=False,
    )
    domain: ChatSessionDomain = Field(
        default=ChatSessionDomain.UNKNOWN,
        max_length=32,
        nullable=False,
    )
    status: ChatSessionStatus = Field(
        default=ChatSessionStatus.ACTIVE,
        max_length=32,
        nullable=False,
    )
    title: str = Field(max_length=512, nullable=False)


class AgentChatMessageTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "agent_chat_messages"
    __table_args__ = (
        Index("ix_agent_chat_messages_session_id", "session_id"),
        Index("ix_agent_chat_messages_created_at", "created_at"),
    )

    session_id: UUID = Field(foreign_key="agent_chat_sessions.id", nullable=False)
    role: AgentChatMessageRole = Field(nullable=False)
    content: str = Field(max_length=65536, nullable=False)
    message_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("message_metadata", JSON, nullable=False),
    )
    agent_run_id: UUID | None = Field(default=None, foreign_key="agent_runs.id", nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
