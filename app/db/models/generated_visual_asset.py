"""Generated visual assets from design.image_generation (Phase H2.6A)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    GeneratedVisualAssetType,
    GeneratedVisualGenerationMode,
    GeneratedVisualAssetStatus,
)


class GeneratedVisualAssetTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "generated_visual_assets"
    __table_args__ = (
        Index("ix_generated_visual_assets_owner_id", "owner_id"),
        Index("ix_generated_visual_assets_user_request_id", "user_request_id"),
        Index("ix_generated_visual_assets_status", "status"),
        Index("ix_generated_visual_assets_generation_mode", "generation_mode"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    user_request_id: UUID = Field(foreign_key="user_requests.id", nullable=False)
    skill_code: str = Field(max_length=128, nullable=False)
    skill_version: str = Field(max_length=32, nullable=False)
    knowledge_snapshot_id: UUID | None = Field(
        default=None,
        foreign_key="knowledge_snapshots.id",
    )
    provider: str = Field(max_length=64, nullable=False)
    model: str | None = Field(default=None, max_length=128)
    generation_mode: GeneratedVisualGenerationMode = Field(
        default=GeneratedVisualGenerationMode.MOCK,
        max_length=32,
        nullable=False,
    )
    asset_type: GeneratedVisualAssetType = Field(
        default=GeneratedVisualAssetType.DIAGNOSTIC_PLACEHOLDER,
        max_length=64,
        nullable=False,
    )
    prompt_summary: str = Field(max_length=1000, nullable=False)
    aspect_ratio: str = Field(default="1:1", max_length=32, nullable=False)
    width: int | None = Field(default=None)
    height: int | None = Field(default=None)
    mime_type: str = Field(default="image/png", max_length=64, nullable=False)
    storage_uri: str | None = Field(default=None, max_length=1000)
    content_path: str | None = Field(default=None, max_length=1000)
    checksum: str | None = Field(default=None, max_length=128)
    status: GeneratedVisualAssetStatus = Field(
        default=GeneratedVisualAssetStatus.PENDING,
        nullable=False,
    )
    safety_result: str = Field(default="passed", max_length=64, nullable=False)
    generation_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    error_category: str | None = Field(default=None, max_length=128)
    reference_set_id: UUID | None = Field(default=None, foreign_key="reference_sets.id")
    used_reference_ids: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    excluded_reference_ids: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    identity_similarity: str | None = Field(default=None, max_length=32)
    brand_similarity: str | None = Field(default=None, max_length=32)
    user_accepted: bool | None = Field(default=None)
    review_notes: str | None = Field(default=None, max_length=2000)
    parent_asset_id: UUID | None = Field(
        default=None,
        foreign_key="generated_visual_assets.id",
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
