"""Publishing API request bodies (Phase 6.0)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.publishing.contracts import (
    PublicationJobStatus,
    PublishingChannelStatus,
    PublishingChannelType,
)

REPLAYABLE_PUBLICATION_JOB_STATUSES = frozenset(
    {
        PublicationJobStatus.FAILED,
        PublicationJobStatus.CANCELLED,
    },
)


class PublishingChannelCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    type: PublishingChannelType
    config: dict[str, Any] = Field(default_factory=dict)


class PublishingChannelUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    status: PublishingChannelStatus | None = None
    config: dict[str, Any] | None = None


class PublicationJobCreateRequest(BaseModel):
    asset_id: UUID
    channel_id: UUID
    campaign_id: UUID | None = None
    scheduled_at: datetime | None = None

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("scheduled_at must be an ISO 8601 UTC datetime with timezone")
        # normalize to UTC
        normalized = value.astimezone(UTC)
        if normalized <= datetime.now(UTC):
            raise ValueError("scheduled_at must be in the future")
        return normalized


class PublicationJobRescheduleRequest(BaseModel):
    scheduled_at: datetime

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            raise ValueError("scheduled_at must be an ISO 8601 UTC datetime with timezone")
        normalized = value.astimezone(UTC)
        if normalized <= datetime.now(UTC):
            raise ValueError("scheduled_at must be in the future")
        return normalized


class PublicationJobReplayBatchRequest(BaseModel):
    statuses: list[PublicationJobStatus] = Field(
        default_factory=lambda: [PublicationJobStatus.FAILED],
        min_length=1,
    )
    channel_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=100)

    @field_validator("statuses")
    @classmethod
    def validate_replayable_statuses(
        cls,
        statuses: list[PublicationJobStatus],
    ) -> list[PublicationJobStatus]:
        invalid = [item for item in statuses if item not in REPLAYABLE_PUBLICATION_JOB_STATUSES]
        if invalid:
            msg = "statuses must be failed or cancelled only"
            raise ValueError(msg)
        return statuses


class PublicationJobReplayBatchResponse(BaseModel):
    matched_count: int
    replayed_count: int
    skipped_count: int
