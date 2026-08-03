"""Pilot browser session — hashed token only (CPH.3)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now


class BrowserSessionTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "browser_sessions"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    token_hash: str = Field(max_length=128, index=True, nullable=False, unique=True)
    status: str = Field(default="active", max_length=32, nullable=False, index=True)
    purpose: str = Field(default="pilot_browser", max_length=64, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    expires_at: datetime = Field(nullable=False, index=True)
    last_seen_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
    user_agent_hash: str | None = Field(default=None, max_length=128)
    created_by: str = Field(default="login", max_length=64, nullable=False)
