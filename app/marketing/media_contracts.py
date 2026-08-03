"""Media production domain contracts (Phase AI.50–AI.54)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MediaBriefStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class MediaAssetType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"


class MediaAssetStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"
    GENERATION_FAILED = "generation_failed"


class MediaBrief(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    content_asset_id: UUID
    source_content_asset_id: UUID
    status: MediaBriefStatus = MediaBriefStatus.DRAFT
    title: str
    goal: str = ""
    target_audience: str = ""
    platform: str = ""
    creative_direction: str = ""
    visual_style: str = ""
    composition: str = ""
    text_overlay: str = ""
    references: list[Any] = Field(default_factory=list)
    submitted_for_review_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MediaAsset(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    media_brief_id: UUID
    source_media_brief_id: UUID
    media_type: MediaAssetType
    status: MediaAssetStatus = MediaAssetStatus.DRAFT
    generation_provider: str | None = None
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    source_generation_job_id: UUID | None = None
    provider: str | None = None
    provider_asset_ref: str | None = None
    storage_uri: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    current_version_number: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MediaAssetVersion(BaseModel):
    version_number: int
    media_asset_id: UUID
    source_generation_job_id: UUID | None = None
    storage_uri: str | None = None
    provider_asset_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
