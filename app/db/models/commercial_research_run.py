"""Phase 1B.1 — durable commercial research orchestration run."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import CommercialResearchRunStatus, CommercialResearchStageId


class CommercialResearchRunTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "commercial_research_runs"
    __table_args__ = (
        Index("ix_commercial_research_runs_owner", "owner_id"),
        Index("ix_commercial_research_runs_user_request", "user_request_id"),
        Index("ix_commercial_research_runs_status", "status"),
        UniqueConstraint(
            "owner_id",
            "user_request_id",
            "request_hash",
            name="uq_commercial_research_owner_request_hash",
        ),
        UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_commercial_research_owner_idempotency",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    user_request_id: UUID = Field(foreign_key="user_requests.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    project_brief_id: UUID = Field(foreign_key="project_briefs.id", nullable=False)
    project_brief_version: int = Field(default=1, nullable=False)
    investigation_id: UUID = Field(foreign_key="investigations.id", nullable=False)
    status: CommercialResearchRunStatus = Field(
        default=CommercialResearchRunStatus.DRAFT,
        max_length=32,
        nullable=False,
    )
    current_stage: CommercialResearchStageId = Field(
        default=CommercialResearchStageId.BOOTSTRAP,
        max_length=32,
        nullable=False,
    )
    completed_stages: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    progress_pct: int = Field(default=0, nullable=False)
    request_hash: str = Field(max_length=128, nullable=False)
    run_version: int = Field(default=1, nullable=False)
    idempotency_key: str | None = Field(default=None, max_length=128)
    preflight_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    quote_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    approval_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    provider_operation_id: str | None = Field(default=None, max_length=256)
    error_code: str | None = Field(default=None, max_length=128)
    safe_error_message: str | None = Field(default=None, max_length=2000)
    outcome_unknown: bool = Field(default=False, nullable=False)
    retry_blocked: bool = Field(default=False, nullable=False)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
