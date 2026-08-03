"""Publishing foundation API request bodies (Phase AI.60–AI.63)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.publishing_foundation.contracts import (
    PublishingDispatchMode,
    PublishingFoundationChannelStatus,
    PublishingFoundationChannelType,
)


class PublishingFoundationChannelCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    channel_type: PublishingFoundationChannelType
    config_metadata: dict[str, Any] = Field(default_factory=dict)
    status: PublishingFoundationChannelStatus = PublishingFoundationChannelStatus.DRAFT


class PublishingFoundationChannelUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    status: PublishingFoundationChannelStatus | None = None
    config_metadata: dict[str, Any] | None = None


class SchedulePublicationPackageJobRequest(BaseModel):
    scheduled_for: datetime

    @field_validator("scheduled_for")
    @classmethod
    def validate_scheduled_for(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("scheduled_for must be an ISO 8601 UTC datetime with timezone")
        normalized = value.astimezone(UTC)
        if normalized <= datetime.now(UTC):
            raise ValueError("scheduled_for must be in the future")
        return normalized


class DispatchDuePublicationJobRequest(BaseModel):
    mode: PublishingDispatchMode = PublishingDispatchMode.DRY_RUN
