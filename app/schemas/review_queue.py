"""Human review queue API contracts (Phase 14.0)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.marketing.contracts import ContentAssetStatus
from app.schemas.contracts import ReviewQueueItemType


class ReviewQueueItem(BaseModel):
    type: ReviewQueueItemType = ReviewQueueItemType.CONTENT_ASSET
    id: UUID
    campaign_id: UUID | None = None
    campaign_title: str | None = None
    title: str
    status: ContentAssetStatus
    current_version_number: int
    created_at: datetime
    updated_at: datetime


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem] = Field(default_factory=list)
