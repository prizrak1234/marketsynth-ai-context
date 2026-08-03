"""Password reset token persistence — hash only."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class PasswordResetTokenTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "password_reset_tokens"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    token_hash: str = Field(max_length=128, unique=True, index=True, nullable=False)
    status: str = Field(max_length=32, index=True, nullable=False, default="pending")
    expires_at: datetime = Field(index=True, nullable=False)
    used_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
    requested_ip_hash: str | None = Field(default=None, max_length=128)
    requested_user_agent_hash: str | None = Field(default=None, max_length=128)
