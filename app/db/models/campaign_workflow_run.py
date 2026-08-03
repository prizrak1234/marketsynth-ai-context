"""Campaign workflow run persistence (Phase AI.260)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import CampaignWorkflowRunStatus


class CampaignWorkflowRunTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "campaign_workflow_runs"
    __table_args__ = (
        Index("ix_campaign_workflow_runs_owner_id", "owner_id"),
        Index("ix_campaign_workflow_runs_project_id", "project_id"),
        Index("ix_campaign_workflow_runs_campaign_id", "campaign_id"),
        Index("ix_campaign_workflow_runs_template_id", "template_id"),
        Index("ix_campaign_workflow_runs_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    campaign_id: UUID = Field(foreign_key="campaigns.id", nullable=False)
    template_id: str = Field(max_length=128, nullable=False)
    status: CampaignWorkflowRunStatus = Field(
        default=CampaignWorkflowRunStatus.DRAFT,
        nullable=False,
    )
    current_step_index: int = Field(default=0, nullable=False)
    step_results: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
