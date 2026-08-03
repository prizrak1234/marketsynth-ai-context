"""Marketing campaign API request bodies (Phase 9.0)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.marketing.contracts import MarketingCampaignStatus
from app.publishing.contracts import PublicationJob
from app.schemas.contracts import (
    CampaignWorkflowRecommendedAction,
    CampaignWorkflowState,
)


class MarketingCampaignCreateRequest(BaseModel):
    brief_id: UUID | None = None
    title: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=4096)
    status: MarketingCampaignStatus = MarketingCampaignStatus.DRAFT
    start_at: datetime | None = None
    end_at: datetime | None = None
    campaign_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("start_at", "end_at")
    @classmethod
    def validate_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Campaign datetime must be an ISO 8601 UTC datetime with timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_bounds(self) -> MarketingCampaignCreateRequest:
        if self.start_at is not None and self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("end_at must be greater than start_at")
        return self


class MarketingCampaignUpdateRequest(BaseModel):
    brief_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=4096)
    status: MarketingCampaignStatus | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    campaign_metadata: dict[str, Any] | None = None

    @field_validator("start_at", "end_at")
    @classmethod
    def validate_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Campaign datetime must be an ISO 8601 UTC datetime with timezone")
        return value.astimezone(UTC)


class CampaignAssetListItem(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    brief_id: UUID | None = None
    campaign_id: UUID | None = None
    type: str
    title: str
    status: str
    current_version_number: int
    approved_version_number: int | None = None
    created_at: datetime
    updated_at: datetime


class CampaignOverviewCounts(BaseModel):
    assets_total: int = 0
    assets_draft: int = 0
    assets_approved: int = 0
    assets_archived: int = 0
    jobs_total: int = 0
    jobs_scheduled: int = 0
    jobs_queued: int = 0
    jobs_running: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    jobs_cancelled: int = 0
    jobs_skipped: int = 0


class CampaignOverviewSchedule(BaseModel):
    next_scheduled_publication_at: datetime | None = None
    last_successful_publication_at: datetime | None = None


class CampaignOverviewResponse(BaseModel):
    campaign: dict
    counts: CampaignOverviewCounts = Field(default_factory=CampaignOverviewCounts)
    schedule: CampaignOverviewSchedule = Field(default_factory=CampaignOverviewSchedule)
    recent_jobs: list[PublicationJob] = Field(default_factory=list)


class CampaignWorkflowCounts(BaseModel):
    plan_drafts: int = 0
    assets_total: int = 0
    assets_approved: int = 0
    assets_draft: int = 0
    pending_review_assets: int = 0


class CampaignWorkflowResponse(BaseModel):
    campaign_id: UUID
    workflow_state: CampaignWorkflowState
    counts: CampaignWorkflowCounts = Field(default_factory=CampaignWorkflowCounts)
    next_recommended_action: CampaignWorkflowRecommendedAction

