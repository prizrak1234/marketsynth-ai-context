"""Investigation persistence (Commercial MVP P0.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import (
    InvestigationReadinessStatus,
    InvestigationStageId,
    InvestigationStatus,
)


class InvestigationTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "investigations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "version",
            name="uq_investigations_project_version",
        ),
        Index("ix_investigations_owner_id", "owner_id"),
        Index("ix_investigations_project_id", "project_id"),
        Index("ix_investigations_project_brief_id", "project_brief_id"),
        Index("ix_investigations_project_id_status", "project_id", "status"),
        Index("ix_investigations_project_id_current_stage", "project_id", "current_stage"),
        Index("ix_investigations_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    project_brief_id: UUID = Field(foreign_key="project_briefs.id", nullable=False)
    project_brief_version: int = Field(nullable=False)
    input_fingerprint: str = Field(max_length=128, nullable=False)
    version: int = Field(nullable=False)
    status: InvestigationStatus = Field(
        default=InvestigationStatus.DRAFT,
        nullable=False,
    )
    current_stage: InvestigationStageId = Field(
        default=InvestigationStageId.PROJECT_CONTEXT,
        nullable=False,
    )
    stages: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    readiness_status: InvestigationReadinessStatus = Field(
        default=InvestigationReadinessStatus.NOT_READY,
        nullable=False,
    )
    readiness_reasons: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    started_at: datetime | None = Field(default=None, nullable=True)
    completed_at: datetime | None = Field(default=None, nullable=True)
    blocked_reason: str | None = Field(default=None, max_length=2000, nullable=True)
    supersedes_investigation_id: UUID | None = Field(
        default=None,
        foreign_key="investigations.id",
        nullable=True,
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
