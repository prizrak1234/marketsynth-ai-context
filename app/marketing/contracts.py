"""Marketing domain contracts — Pydantic models (Phase 4.0)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MarketingBriefStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ContentAssetType(StrEnum):
    LANDING_PAGE = "landing_page"
    AD_COPY = "ad_copy"
    EMAIL = "email"
    TELEGRAM_POST = "telegram_post"
    ARTICLE = "article"
    OFFER = "offer"
    AUDIENCE_PROFILE = "audience_profile"
    FUNNEL_STEP = "funnel_step"


class ContentAssetStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ContentAssetVersionSource(StrEnum):
    HTTP_API = "http_api"
    AGENT_TOOL = "agent_tool"
    SYSTEM = "system"


class MarketingBrief(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    title: str
    product_description: str = ""
    target_audience: str = ""
    offer: str = ""
    goals: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    status: MarketingBriefStatus = MarketingBriefStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContentAsset(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    brief_id: UUID | None = None
    campaign_id: UUID | None = None
    task_id: UUID | None = None
    agent_run_id: UUID | None = None
    type: ContentAssetType
    title: str
    body: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: ContentAssetStatus = ContentAssetStatus.DRAFT
    current_version_number: int = 1
    approved_version_number: int | None = None
    source_asset_id: UUID | None = None
    source_version_number: int | None = None
    revision_number: int | None = None
    source_marketing_plan_id: UUID | None = None
    source_execution_run_id: UUID | None = None
    source_specialist_output_id: UUID | None = None
    source_specialist_type: str | None = None
    submitted_for_review_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PublicationPackageChannel(StrEnum):
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    BLOG = "blog"


class PublicationPackageStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class PublicationPackage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    content_asset_id: UUID
    source_content_asset_id: UUID
    channel: PublicationPackageChannel
    title: str
    body: str = ""
    cta: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: PublicationPackageStatus = PublicationPackageStatus.DRAFT
    submitted_for_review_at: datetime | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContentAssetVersion(BaseModel):
    version_number: int
    title: str
    body: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by_source: ContentAssetVersionSource
    created_at: datetime


class ContentAssetDiffSide(BaseModel):
    asset_id: UUID
    version_number: int | None = None
    title: str
    status: ContentAssetStatus
    type: ContentAssetType


class ContentAssetMetadataDiff(BaseModel):
    added: dict[str, Any] = Field(default_factory=dict)
    removed: dict[str, Any] = Field(default_factory=dict)
    changed: dict[str, Any] = Field(default_factory=dict)


class ContentAssetDiffDetail(BaseModel):
    title_changed: bool
    body_changed: bool
    metadata_changed: bool
    body_diff: dict[str, Any]
    metadata_diff: ContentAssetMetadataDiff


class ContentAssetDiffResponse(BaseModel):
    model_config = {"populate_by_name": True}

    from_: ContentAssetDiffSide = Field(alias="from")
    to: ContentAssetDiffSide
    diff: ContentAssetDiffDetail


class MarketingCampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MarketingCampaign(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    brief_id: UUID | None = None
    title: str
    description: str | None = None
    status: MarketingCampaignStatus = MarketingCampaignStatus.DRAFT
    start_at: datetime | None = None
    end_at: datetime | None = None
    campaign_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CampaignPlanDraftStatus(StrEnum):
    DRAFT = "draft"
    ARCHIVED = "archived"


class CampaignPlanDraft(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    campaign_id: UUID
    source_agent_run_id: UUID | None = None
    title: str
    plan_payload: dict[str, Any] = Field(default_factory=dict)
    status: CampaignPlanDraftStatus = CampaignPlanDraftStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
