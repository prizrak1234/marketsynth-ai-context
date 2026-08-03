"""Memory item persistence — mirrors app.schemas.contracts.MemoryItem."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import MemoryLayer


class MemoryItemTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "memory_items"

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID | None = Field(default=None, foreign_key="projects.id", index=True)
    layer: MemoryLayer = Field(nullable=False, index=True)
    key: str = Field(max_length=255, nullable=False, index=True)
    content: str = Field(nullable=False)
    item_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    expires_at: datetime | None = Field(default=None, index=True)
