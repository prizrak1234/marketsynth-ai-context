"""ProjectBrief persistence (Commercial MVP P0.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import ProjectBriefReadinessStatus, ProjectBriefStatus


class ProjectBriefTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "project_briefs"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "version",
            name="uq_project_briefs_project_version",
        ),
        Index("ix_project_briefs_owner_id", "owner_id"),
        Index("ix_project_briefs_project_id", "project_id"),
        Index("ix_project_briefs_project_id_status", "project_id", "status"),
        Index("ix_project_briefs_input_fingerprint", "input_fingerprint"),
        Index("ix_project_briefs_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    version: int = Field(nullable=False)
    status: ProjectBriefStatus = Field(
        default=ProjectBriefStatus.DRAFT,
        nullable=False,
    )
    language: str = Field(default="ru", max_length=16, nullable=False)
    project_basics: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    product: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    market: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    audience: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    economics: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    materials_summary: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    assumptions: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    missing_data: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    readiness_status: ProjectBriefReadinessStatus = Field(
        default=ProjectBriefReadinessStatus.INSUFFICIENT_DATA,
        nullable=False,
    )
    readiness_reasons: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    input_fingerprint: str = Field(max_length=128, nullable=False)
    supersedes_brief_id: UUID | None = Field(
        default=None,
        foreign_key="project_briefs.id",
        nullable=True,
    )
    submitted_at: datetime | None = Field(default=None, nullable=True)
