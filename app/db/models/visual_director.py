"""Visual Director persistence (PRODUCT-CD-RUNTIME-02 Image Golden Path)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    ImageAssetStatus,
    VisualAspectRatio,
    VisualFormat,
    VisualRequestContextSource,
    VisualRunStatus,
)


class VisualRequestTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "visual_requests"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "version",
            name="uq_visual_requests_project_version",
        ),
        Index("ix_visual_requests_owner_id", "owner_id"),
        Index("ix_visual_requests_project_id", "project_id"),
        Index("ix_visual_requests_current_run_id", "current_run_id"),
        Index("ix_visual_requests_approved_asset_id", "approved_asset_id"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    version: int = Field(default=1, nullable=False)
    context_source: VisualRequestContextSource = Field(
        default=VisualRequestContextSource.MANUAL,
        nullable=False,
    )
    title: str = Field(max_length=240, nullable=False)
    objective: str = Field(max_length=2000, nullable=False)
    scene_description: str = Field(max_length=4000, nullable=False)
    subject: str = Field(max_length=1000, nullable=False)
    style: str = Field(default="clean commercial", max_length=240, nullable=False)
    audience: str = Field(max_length=2000, nullable=False)
    mood: str = Field(default="confident", max_length=240, nullable=False)
    aspect_ratio: VisualAspectRatio = Field(
        default=VisualAspectRatio.RATIO_1_1,
        nullable=False,
    )
    visual_format: VisualFormat = Field(
        default=VisualFormat.SOCIAL_POST_IMAGE,
        nullable=False,
    )
    requested_variants: int = Field(default=2, nullable=False)
    text_overlay: str = Field(default="", max_length=500, nullable=False)
    must_include: str = Field(default="", max_length=2000, nullable=False)
    must_avoid: str = Field(default="", max_length=2000, nullable=False)
    related_text_asset_id: UUID | None = Field(default=None, nullable=True)
    reference_asset_ids: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    language: str = Field(default="ru", max_length=16, nullable=False)
    current_run_id: UUID | None = Field(default=None, nullable=True)
    approved_asset_id: UUID | None = Field(default=None, nullable=True)
    approved_version_number: int | None = Field(default=None, nullable=True)


class VisualInputSnapshotTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "visual_input_snapshots"
    __table_args__ = (
        Index("ix_visual_input_snapshots_request_id", "visual_request_id"),
        Index(
            "ix_visual_input_snapshots_request_version",
            "visual_request_id",
            "visual_request_version",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    visual_request_id: UUID = Field(foreign_key="visual_requests.id", nullable=False)
    visual_request_version: int = Field(nullable=False)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class VisualRunTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "visual_runs"
    __table_args__ = (
        Index("ix_visual_runs_owner_id", "owner_id"),
        Index("ix_visual_runs_project_id", "project_id"),
        Index("ix_visual_runs_request_id", "visual_request_id"),
        Index("ix_visual_runs_status", "status"),
        Index("ix_visual_runs_idempotency_key", "idempotency_key"),
        Index("ix_visual_runs_request_active", "visual_request_id", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    visual_request_id: UUID = Field(foreign_key="visual_requests.id", nullable=False)
    visual_request_version: int = Field(nullable=False)
    snapshot_id: UUID = Field(foreign_key="visual_input_snapshots.id", nullable=False)
    status: VisualRunStatus = Field(default=VisualRunStatus.QUEUED, nullable=False)
    attempt: int = Field(default=1, nullable=False)
    error_code: str | None = Field(default=None, max_length=128, nullable=True)
    error_message: str | None = Field(default=None, max_length=2000, nullable=True)
    provider: str | None = Field(default=None, max_length=64, nullable=True)
    model: str | None = Field(default=None, max_length=128, nullable=True)
    idempotency_key: str | None = Field(default=None, max_length=128, nullable=True)
    completed_at: datetime | None = Field(default=None, nullable=True)


class ImageAssetTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "image_assets"
    __table_args__ = (
        Index("ix_image_assets_owner_id", "owner_id"),
        Index("ix_image_assets_project_id", "project_id"),
        Index("ix_image_assets_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    title: str = Field(max_length=512, nullable=False)
    status: ImageAssetStatus = Field(default=ImageAssetStatus.DRAFT, nullable=False)
    current_version_number: int = Field(default=1, nullable=False)
    approved_version_number: int | None = Field(default=None, nullable=True)
    mime_type: str = Field(default="image/png", max_length=64, nullable=False)
    width: int | None = Field(default=None, nullable=True)
    height: int | None = Field(default=None, nullable=True)
    content_path: str | None = Field(default=None, max_length=1000, nullable=True)
    checksum: str | None = Field(default=None, max_length=128, nullable=True)
    file_size_bytes: int | None = Field(default=None, nullable=True)
    asset_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class ImageAssetVersionTable(UUIDPrimaryKeyMixin, table=True):
    __tablename__ = "image_asset_versions"
    __table_args__ = (
        UniqueConstraint(
            "image_asset_id",
            "version_number",
            name="uq_image_asset_versions_asset_version",
        ),
        Index("ix_image_asset_versions_asset_id", "image_asset_id"),
    )

    image_asset_id: UUID = Field(foreign_key="image_assets.id", nullable=False)
    version_number: int = Field(nullable=False)
    mime_type: str = Field(default="image/png", max_length=64, nullable=False)
    width: int | None = Field(default=None, nullable=True)
    height: int | None = Field(default=None, nullable=True)
    content_path: str = Field(max_length=1000, nullable=False)
    checksum: str = Field(max_length=128, nullable=False)
    file_size_bytes: int = Field(nullable=False)
    asset_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    created_by: UUID | None = Field(default=None, nullable=True)


class VisualRunCandidateTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "visual_run_candidates"
    __table_args__ = (
        UniqueConstraint(
            "visual_run_id",
            "candidate_index",
            name="uq_visual_run_candidates_run_index",
        ),
        Index("ix_visual_run_candidates_run_id", "visual_run_id"),
        Index("ix_visual_run_candidates_asset_id", "image_asset_id"),
        Index("ix_visual_run_candidates_request_id", "visual_request_id"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    visual_request_id: UUID = Field(foreign_key="visual_requests.id", nullable=False)
    visual_request_version: int = Field(nullable=False)
    visual_run_id: UUID = Field(foreign_key="visual_runs.id", nullable=False)
    image_asset_id: UUID = Field(foreign_key="image_assets.id", nullable=False)
    candidate_index: int = Field(nullable=False)
    rejected: bool = Field(default=False, nullable=False)
