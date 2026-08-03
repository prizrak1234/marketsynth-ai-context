"""VS.2A — durable commercial single-clip request (preview → approval → execution)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import VideoClipRequestStatus


class VideoClipRequestTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "video_clip_requests"
    __table_args__ = (
        Index("ix_video_clip_requests_owner", "owner_id"),
        Index("ix_video_clip_requests_status", "status"),
        UniqueConstraint("owner_id", "idempotency_key", name="uq_video_clip_owner_idempotency"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID | None = Field(default=None, foreign_key="projects.id")
    user_request_id: UUID | None = Field(default=None, foreign_key="user_requests.id")
    source_image_asset_id: UUID = Field(foreign_key="generated_visual_assets.id", nullable=False)
    motion_brief: str = Field(sa_column=Column(Text, nullable=False))
    duration_seconds: int = Field(default=8, nullable=False)
    aspect_ratio: str = Field(default="16:9", max_length=16, nullable=False)
    request_hash: str = Field(max_length=128, nullable=False)
    preview_snapshot_json: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    estimated_cost_units: str | None = Field(default=None, max_length=32)
    quote_at: datetime | None = Field(default=None)
    status: VideoClipRequestStatus = Field(
        default=VideoClipRequestStatus.PREVIEW,
        max_length=32,
        nullable=False,
    )
    idempotency_key: str | None = Field(default=None, max_length=128)
    approved_at: datetime | None = Field(default=None)
    approved_request_hash: str | None = Field(default=None, max_length=128)
    provider_job_id: str | None = Field(default=None, max_length=256)
    provider_code: str | None = Field(default=None, max_length=64)
    execution_evidence_json: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    scene_graph_json: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    result_asset_id: UUID | None = Field(default=None, foreign_key="generated_visual_assets.id")
    error_code: str | None = Field(default=None, max_length=128)
    error_message_ru: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
