"""API key persistence model — mirrors app.schemas.contracts.ApiKey."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now


class ApiKeyTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "api_keys"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    name: str = Field(max_length=255, nullable=False)
    key_hash: str = Field(max_length=128, nullable=False)
    key_prefix: str = Field(max_length=32, index=True, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    last_used_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
