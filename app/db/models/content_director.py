"""Content Director persistence (PRODUCT-CD-RUNTIME-01 Text Golden Path)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import (
    ContentDirectorChannel,
    ContentDirectorContentType,
    ContentRequestContextSource,
    ContentRunStatus,
)


class ContentRequestTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "content_requests"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "version",
            name="uq_content_requests_project_version",
        ),
        Index("ix_content_requests_owner_id", "owner_id"),
        Index("ix_content_requests_project_id", "project_id"),
        Index("ix_content_requests_current_run_id", "current_run_id"),
        Index("ix_content_requests_approved_asset_id", "approved_asset_id"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    version: int = Field(default=1, nullable=False)
    context_source: ContentRequestContextSource = Field(
        default=ContentRequestContextSource.MANUAL,
        nullable=False,
    )
    title: str = Field(max_length=240, nullable=False)
    objective: str = Field(max_length=2000, nullable=False)
    channel: ContentDirectorChannel = Field(
        default=ContentDirectorChannel.TELEGRAM,
        nullable=False,
    )
    content_type: ContentDirectorContentType = Field(
        default=ContentDirectorContentType.TELEGRAM_POST,
        nullable=False,
    )
    audience_description: str = Field(max_length=2000, nullable=False)
    key_message: str = Field(max_length=2000, nullable=False)
    offer_value_proposition: str = Field(default="", max_length=2000, nullable=False)
    tone: str = Field(default="professional", max_length=120, nullable=False)
    language: str = Field(default="ru", max_length=16, nullable=False)
    length: str = Field(default="medium", max_length=64, nullable=False)
    cta: str = Field(default="", max_length=500, nullable=False)
    must_include: str = Field(default="", max_length=2000, nullable=False)
    must_avoid: str = Field(default="", max_length=2000, nullable=False)
    requested_variants: int = Field(default=2, nullable=False)
    current_run_id: UUID | None = Field(default=None, nullable=True)
    approved_asset_id: UUID | None = Field(default=None, nullable=True)
    approved_version_number: int | None = Field(default=None, nullable=True)


class ContentInputSnapshotTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "content_input_snapshots"
    __table_args__ = (
        Index("ix_content_input_snapshots_request_id", "content_request_id"),
        Index(
            "ix_content_input_snapshots_request_version",
            "content_request_id",
            "content_request_version",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    content_request_id: UUID = Field(foreign_key="content_requests.id", nullable=False)
    content_request_version: int = Field(nullable=False)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class ContentRunTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "content_runs"
    __table_args__ = (
        Index("ix_content_runs_owner_id", "owner_id"),
        Index("ix_content_runs_project_id", "project_id"),
        Index("ix_content_runs_request_id", "content_request_id"),
        Index("ix_content_runs_status", "status"),
        Index("ix_content_runs_idempotency_key", "idempotency_key"),
        Index(
            "ix_content_runs_request_active",
            "content_request_id",
            "status",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    content_request_id: UUID = Field(foreign_key="content_requests.id", nullable=False)
    content_request_version: int = Field(nullable=False)
    snapshot_id: UUID = Field(foreign_key="content_input_snapshots.id", nullable=False)
    status: ContentRunStatus = Field(default=ContentRunStatus.QUEUED, nullable=False)
    attempt: int = Field(default=1, nullable=False)
    error_code: str | None = Field(default=None, max_length=128, nullable=True)
    error_message: str | None = Field(default=None, max_length=2000, nullable=True)
    provider: str | None = Field(default=None, max_length=64, nullable=True)
    model: str | None = Field(default=None, max_length=128, nullable=True)
    idempotency_key: str | None = Field(default=None, max_length=128, nullable=True)
    completed_at: datetime | None = Field(default=None, nullable=True)


class ContentRunCandidateTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "content_run_candidates"
    __table_args__ = (
        UniqueConstraint(
            "content_run_id",
            "candidate_index",
            name="uq_content_run_candidates_run_index",
        ),
        Index("ix_content_run_candidates_run_id", "content_run_id"),
        Index("ix_content_run_candidates_asset_id", "content_asset_id"),
        Index("ix_content_run_candidates_request_id", "content_request_id"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    content_request_id: UUID = Field(foreign_key="content_requests.id", nullable=False)
    content_request_version: int = Field(nullable=False)
    content_run_id: UUID = Field(foreign_key="content_runs.id", nullable=False)
    content_asset_id: UUID = Field(foreign_key="content_assets.id", nullable=False)
    candidate_index: int = Field(nullable=False)
    rejected: bool = Field(default=False, nullable=False)
