"""Business campaign persistence (Phase AI.147)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import CampaignStatus


class CampaignTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_owner_id", "owner_id"),
        Index("ix_campaigns_project_id", "project_id"),
        Index("ix_campaigns_status", "status"),
        Index("ix_campaigns_scenario_id", "scenario_id"),
        Index("ix_campaigns_name", "name"),
        Index("ix_campaigns_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    name: str = Field(max_length=256, nullable=False)
    goal: str = Field(max_length=4096, nullable=False)
    scenario_id: str | None = Field(default=None, max_length=128, nullable=True)
    status: CampaignStatus = Field(default=CampaignStatus.DRAFT, nullable=False)
    campaign_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
