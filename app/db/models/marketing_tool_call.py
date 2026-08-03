"""Marketing data tool call persistence (Phase AI.217)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import MarketingToolCallStatus, MarketingToolType


class MarketingToolCallTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_tool_calls"
    __table_args__ = (
        Index("ix_marketing_tool_calls_owner_id", "owner_id"),
        Index("ix_marketing_tool_calls_project_id", "project_id"),
        Index("ix_marketing_tool_calls_tool_type", "tool_type"),
        Index("ix_marketing_tool_calls_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    tool_type: MarketingToolType = Field(nullable=False)
    input_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    output_payload: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    status: MarketingToolCallStatus = Field(default=MarketingToolCallStatus.QUEUED, nullable=False)
    safe_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    error: str | None = Field(default=None, max_length=512, nullable=True)
    started_at: datetime | None = Field(default=None, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
