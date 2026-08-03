"""Publishing provider contracts (Phase AI.70)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PublishingProviderType(StrEnum):
    DRY_RUN = "dry_run"
    TELEGRAM = "telegram"


class PublishingExecutionInput(BaseModel):
    job_id: UUID
    owner_id: UUID
    project_id: UUID
    publication_package_id: UUID
    channel_id: UUID
    channel_type: str
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)
    channel_config: dict[str, Any] = Field(default_factory=dict)


class PublishingExecutionResult(BaseModel):
    success: bool
    provider: PublishingProviderType
    result_metadata: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None
