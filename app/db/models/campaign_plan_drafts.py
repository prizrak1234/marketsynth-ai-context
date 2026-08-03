"""Campaign plan draft persistence (Phase 10.1)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.marketing.contracts import CampaignPlanDraftStatus


class CampaignPlanDraftTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "campaign_plan_drafts"
    __table_args__ = (
        Index("ix_campaign_plan_drafts_owner_id", "owner_id"),
        Index("ix_campaign_plan_drafts_project_id", "project_id"),
        Index("ix_campaign_plan_drafts_campaign_id", "campaign_id"),
        Index("ix_campaign_plan_drafts_status", "status"),
        Index("ix_campaign_plan_drafts_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    campaign_id: UUID = Field(foreign_key="marketing_campaigns.id", nullable=False)
    source_agent_run_id: UUID | None = Field(
        default=None,
        foreign_key="agent_runs.id",
        nullable=True,
    )

    title: str = Field(max_length=512, nullable=False)
    plan_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: CampaignPlanDraftStatus = Field(
        default=CampaignPlanDraftStatus.DRAFT,
        nullable=False,
    )
