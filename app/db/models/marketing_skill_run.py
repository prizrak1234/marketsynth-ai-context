"""Marketing skill run persistence (Phase AI.227)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import MarketingSkillRunStatus, MarketingSkillType


class MarketingSkillRunTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_skill_runs"
    __table_args__ = (
        Index("ix_marketing_skill_runs_owner_id", "owner_id"),
        Index("ix_marketing_skill_runs_project_id", "project_id"),
        Index("ix_marketing_skill_runs_campaign_id", "campaign_id"),
        Index("ix_marketing_skill_runs_skill_type", "skill_type"),
        Index("ix_marketing_skill_runs_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    campaign_id: UUID | None = Field(default=None, foreign_key="campaigns.id", nullable=True)
    skill_type: MarketingSkillType = Field(nullable=False)
    input_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    output_payload: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    used_tool_call_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    status: MarketingSkillRunStatus = Field(default=MarketingSkillRunStatus.QUEUED, nullable=False)
    safe_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    error: str | None = Field(default=None, max_length=512, nullable=True)
    started_at: datetime | None = Field(default=None, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
