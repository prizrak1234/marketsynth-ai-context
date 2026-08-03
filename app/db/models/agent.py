"""Agent persistence model — mirrors app.schemas.contracts.Agent."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import AgentStatus, AgentType


class AgentTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "agents"

    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    type: AgentType = Field(nullable=False, index=True)
    name: str = Field(max_length=255, nullable=False)
    description: str | None = Field(default=None)
    status: AgentStatus = Field(default=AgentStatus.DRAFT, nullable=False, index=True)
    config: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    capabilities: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
