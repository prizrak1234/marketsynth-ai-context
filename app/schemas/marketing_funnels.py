"""Marketing funnel API request bodies (Phase 4.8)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.marketing.funnel_contracts import (
    FunnelStepAssetRole,
    FunnelStepStatus,
    FunnelStepType,
    MarketingFunnelStatus,
)


class MarketingFunnelCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str = ""
    brief_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketingFunnelUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    brief_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    status: MarketingFunnelStatus | None = None


class MarketingFunnelStepCreateRequest(BaseModel):
    step_type: FunnelStepType
    title: str = Field(min_length=1, max_length=512)
    description: str = ""
    position: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketingFunnelStepUpdateRequest(BaseModel):
    step_type: FunnelStepType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    position: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] | None = None
    status: FunnelStepStatus | None = None


class MarketingFunnelStepReorderRequest(BaseModel):
    step_ids: list[UUID] = Field(min_length=1)


class FunnelStepAssetLinkCreateRequest(BaseModel):
    asset_id: UUID
    role: FunnelStepAssetRole = FunnelStepAssetRole.PRIMARY
