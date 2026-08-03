"""Project persistence model — mirrors app.schemas.contracts.Project."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class ProjectTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "projects"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    name: str = Field(max_length=255, nullable=False)
    description: str | None = Field(default=None)
    config: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
