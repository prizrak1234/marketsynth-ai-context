"""Marketing funnel domain contracts (Phase 4.8)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MarketingFunnelStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class FunnelStepType(StrEnum):
    AWARENESS = "awareness"
    LEAD_MAGNET = "lead_magnet"
    NURTURE = "nurture"
    OFFER = "offer"
    CHECKOUT = "checkout"
    ONBOARDING = "onboarding"
    RETENTION = "retention"
    REACTIVATION = "reactivation"


class FunnelStepStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class FunnelStepAssetRole(StrEnum):
    PRIMARY = "primary"
    SUPPORTING = "supporting"
    TEST_VARIANT = "test_variant"
    REFERENCE = "reference"


class MarketingFunnel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    brief_id: UUID | None = None
    title: str
    description: str = ""
    status: MarketingFunnelStatus = MarketingFunnelStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketingFunnelStep(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    funnel_id: UUID
    step_type: FunnelStepType
    title: str
    description: str = ""
    position: int
    status: FunnelStepStatus = FunnelStepStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FunnelStepAssetLink(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    funnel_id: UUID
    step_id: UUID
    asset_id: UUID
    role: FunnelStepAssetRole = FunnelStepAssetRole.PRIMARY
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FunnelStepLinkedAsset(BaseModel):
    link_id: UUID
    asset_id: UUID
    role: FunnelStepAssetRole
    asset_title: str
    asset_type: str
    asset_status: str
    created_at: datetime
