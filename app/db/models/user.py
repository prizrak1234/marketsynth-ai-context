"""User persistence model — mirrors app.schemas.contracts.User."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import BetaAccessStatus, UserRole


class UserTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "users"

    telegram_id: int | None = Field(default=None, unique=True, index=True)
    email: str | None = Field(default=None, max_length=320, index=True)
    display_name: str | None = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.MEMBER, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    beta_access_status: BetaAccessStatus = Field(
        default=BetaAccessStatus.PENDING,
        nullable=False,
    )
    beta_notes: str | None = Field(default=None, max_length=1024)
    onboarding_manual_completed: list[Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    # CPH.3 — pilot browser login (never expose via API contracts)
    password_hash: str | None = Field(default=None, max_length=255)
    last_login_at: datetime | None = Field(default=None)
    # Set on invite acceptance (email proven by invitation binding)
    email_verified_at: datetime | None = Field(default=None)
