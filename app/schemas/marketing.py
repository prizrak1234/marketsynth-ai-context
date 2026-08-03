"""Marketing domain API request bodies (Phase 4.0)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.marketing.contracts import (
    ContentAssetStatus,
    ContentAssetType,
    MarketingBriefStatus,
)


class MarketingBriefCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    product_description: str = ""
    target_audience: str = ""
    offer: str = ""
    goals: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class MarketingBriefUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    product_description: str | None = None
    target_audience: str | None = None
    offer: str | None = None
    goals: list[str] | None = None
    constraints: dict[str, Any] | None = None
    status: MarketingBriefStatus | None = None


class ContentAssetCreateRequest(BaseModel):
    brief_id: UUID | None = None
    campaign_id: UUID | None = None
    task_id: UUID | None = None
    agent_run_id: UUID | None = None
    type: ContentAssetType
    title: str = Field(min_length=1, max_length=512)
    body: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: ContentAssetStatus = ContentAssetStatus.DRAFT


class ContentAssetCreateRevisionRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    body: str | None = None
    metadata: dict[str, Any] | None = None


class ContentAssetManualRevisionRequest(BaseModel):
    """Human UI/API manual edit of draft content (Phase UI.9) — new version, no auto-approve."""

    title: str = Field(min_length=1, max_length=512)
    body: str = ""
    metadata_patch: dict[str, Any] = Field(default_factory=dict)


class ContentAssetRollbackRequest(BaseModel):
    version_number: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=256)


class CreateMediaBriefRequest(BaseModel):
    """Explicit approved asset → media brief draft (Phase AI.51)."""

    title: str | None = Field(default=None, min_length=1, max_length=512)
    goal: str | None = None
    target_audience: str | None = None
    platform: str | None = Field(default=None, max_length=128)
    creative_direction: str | None = None
    visual_style: str | None = None
    composition: str | None = None
    text_overlay: str | None = None
    references: list[Any] = Field(default_factory=list)


class CreateMediaAssetRequest(BaseModel):
    """Explicit approved brief → placeholder media asset (Phase AI.54)."""

    media_type: str = Field(min_length=1, max_length=32)


class CreatePublicationPackageRequest(BaseModel):
    """Explicit approved asset → publication package draft (Phase AI.44)."""

    channel: str = Field(min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=512)
    body: str | None = None
    cta: str | None = Field(default=None, max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContentAssetUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    body: str | None = None
    metadata: dict[str, Any] | None = None
    status: ContentAssetStatus | None = None
    brief_id: UUID | None = None
    campaign_id: UUID | None = None
    task_id: UUID | None = None
    agent_run_id: UUID | None = None
