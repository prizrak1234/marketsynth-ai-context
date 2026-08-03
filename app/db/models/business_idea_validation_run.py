"""CMVP.1 — durable Business Idea Validation run."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, String, UniqueConstraint, text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import BusinessIdeaValidationRunStatus


class BusinessIdeaValidationRunTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "business_idea_validation_runs"
    __table_args__ = (
        Index("ix_biv_runs_owner", "owner_id"),
        Index("ix_biv_runs_user_request", "user_request_id"),
        UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_biv_runs_owner_idempotency",
        ),
        Index(
            "uq_biv_one_active_run_per_project",
            "project_id",
            unique=True,
            sqlite_where=text("status IN ('queued', 'running')"),
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    tenant_id: UUID = Field(nullable=False)
    user_request_id: UUID = Field(foreign_key="user_requests.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    investigation_id: UUID = Field(foreign_key="investigations.id", nullable=False)
    business_verdict_id: UUID | None = Field(
        default=None,
        foreign_key="business_verdicts.id",
    )
    analysis_context_id: UUID | None = Field(
        default=None,
        foreign_key="analysis_contexts.id",
    )
    input_snapshot_hash: str | None = Field(default=None, max_length=64)
    idempotency_key: str = Field(max_length=128, nullable=False)
    # Alembic stores status as VARCHAR(32); avoid PG native enum casts at query time.
    status: BusinessIdeaValidationRunStatus = Field(
        sa_column=Column(String(32), nullable=False),
        default=BusinessIdeaValidationRunStatus.QUEUED,
    )
    result_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    error_code: str | None = Field(default=None, max_length=128)
    safe_error_message: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
    finished_at: datetime | None = Field(default=None)
    parent_run_id: UUID | None = Field(default=None)
    research_mode: str | None = Field(default=None, max_length=32)
    progress_json: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    observability_json: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
