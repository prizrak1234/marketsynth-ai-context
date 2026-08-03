"""Scenario wizard run persistence (Phase AI.137)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import ScenarioWizardRunStatus


class ScenarioWizardRunTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "scenario_wizard_runs"
    __table_args__ = (
        Index("ix_scenario_wizard_runs_owner_id", "owner_id"),
        Index("ix_scenario_wizard_runs_project_id", "project_id"),
        Index("ix_scenario_wizard_runs_scenario_id", "scenario_id"),
        Index("ix_scenario_wizard_runs_source_campaign_id", "source_campaign_id"),
        Index("ix_scenario_wizard_runs_status", "status"),
        Index("ix_scenario_wizard_runs_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    scenario_id: str = Field(max_length=128, nullable=False)
    scenario_name: str = Field(max_length=256, nullable=False)
    source_campaign_id: UUID | None = Field(
        default=None,
        foreign_key="campaigns.id",
        nullable=True,
    )
    status: ScenarioWizardRunStatus = Field(
        default=ScenarioWizardRunStatus.DRAFT,
        nullable=False,
    )
    current_step: str = Field(max_length=64, nullable=False)
    step_results: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    failure_reason: str | None = Field(default=None, max_length=1024, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
