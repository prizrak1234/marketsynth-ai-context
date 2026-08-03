"""Pilot invite persistence — one-time activation tokens (hash only)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class PilotInviteTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "pilot_invites"

    email_normalized: str = Field(max_length=320, index=True, nullable=False)
    token_hash: str = Field(max_length=128, unique=True, index=True, nullable=False)
    status: str = Field(max_length=32, index=True, nullable=False, default="pending")
    # Role assigned on accept: member (default) or owner (operator --grant-owner bootstrap)
    grant_role: str = Field(max_length=32, nullable=False, default="member")
    expires_at: datetime = Field(index=True, nullable=False)
    created_by_user_id: UUID | None = Field(default=None, foreign_key="users.id")
    accepted_by_user_id: UUID | None = Field(default=None, foreign_key="users.id")
    accepted_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
