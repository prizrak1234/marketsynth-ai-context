"""Beta feedback report persistence (Phase AI.91)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    BetaFeedbackSeverity,
    BetaFeedbackSource,
    BetaFeedbackStatus,
)


class BetaFeedbackReportTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "beta_feedback_reports"
    __table_args__ = (
        Index("ix_beta_feedback_reports_owner_id", "owner_id"),
        Index("ix_beta_feedback_reports_project_id", "project_id"),
        Index("ix_beta_feedback_reports_status", "status"),
        Index("ix_beta_feedback_reports_source", "source"),
        Index("ix_beta_feedback_reports_severity", "severity"),
        Index("ix_beta_feedback_reports_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID | None = Field(default=None, foreign_key="projects.id", nullable=True)
    source: BetaFeedbackSource = Field(default=BetaFeedbackSource.OTHER, nullable=False)
    severity: BetaFeedbackSeverity = Field(
        default=BetaFeedbackSeverity.MEDIUM,
        nullable=False,
    )
    status: BetaFeedbackStatus = Field(default=BetaFeedbackStatus.OPEN, nullable=False)
    title: str = Field(max_length=256, nullable=False)
    description: str = Field(max_length=4096, nullable=False)
    safe_context: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
