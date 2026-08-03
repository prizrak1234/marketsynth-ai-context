"""Media generation domain contracts (Phase AI.56+)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MediaGenerationProvider(StrEnum):
    MOCK = "mock"
    OPENAI_IMAGES = "openai_images"
    FLUX = "flux"


class MediaGenerationJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaGenerationJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    owner_id: UUID
    project_id: UUID
    media_brief_id: UUID
    media_asset_id: UUID | None = None
    provider: MediaGenerationProvider
    media_type: str
    prompt: str
    status: MediaGenerationJobStatus = MediaGenerationJobStatus.QUEUED
    result_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ImageGenerationInput(BaseModel):
    prompt: str
    model: str | None = None
    size: str = "1024x1024"
    n: int = 1


class ImageGenerationResult(BaseModel):
    provider: str
    safe_metadata: dict[str, Any] = Field(default_factory=dict)
    provider_asset_ref: str | None = None
    storage_uri: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    # Transient decoded image payload (never persist to DB / logs).
    image_bytes: bytes | None = Field(default=None, exclude=True)
