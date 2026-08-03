"""Campaign brief persistence (Phase AI.211)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import CampaignBriefStatus


class CampaignBriefTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "campaign_briefs"
    __table_args__ = (
        Index("ix_campaign_briefs_owner_id", "owner_id"),
        Index("ix_campaign_briefs_project_id", "project_id"),
        Index("ix_campaign_briefs_campaign_id", "campaign_id"),
        Index("ix_campaign_briefs_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    campaign_id: UUID | None = Field(default=None, foreign_key="campaigns.id", nullable=True)
    source_intent: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    source_scenario_id: str | None = Field(default=None, max_length=128, nullable=True)
    status: CampaignBriefStatus = Field(default=CampaignBriefStatus.DRAFT, nullable=False)
    business_name: str | None = Field(default=None, max_length=256, nullable=True)
    industry: str | None = Field(default=None, max_length=128, nullable=True)
    offer: str | None = Field(default=None, max_length=4096, nullable=True)
    target_audience: str | None = Field(default=None, max_length=4096, nullable=True)
    geography: str | None = Field(default=None, max_length=512, nullable=True)
    channels: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    budget_range: str | None = Field(default=None, max_length=256, nullable=True)
    deadline: str | None = Field(default=None, max_length=256, nullable=True)
    constraints: str | None = Field(default=None, max_length=4096, nullable=True)
    success_metric: str | None = Field(default=None, max_length=512, nullable=True)
    goal: str | None = Field(default=None, max_length=128, nullable=True)
    completeness_score: int = Field(default=0, nullable=False)
