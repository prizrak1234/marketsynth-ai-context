"""Beta feedback API request bodies (Phase AI.91–AI.92)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.security import sanitize_text
from app.schemas.contracts import (
    BetaFeedbackSeverity,
    BetaFeedbackSource,
    BetaFeedbackStatus,
)


class BetaFeedbackCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1, max_length=4096)
    project_id: UUID | None = None
    source: BetaFeedbackSource = BetaFeedbackSource.OTHER
    severity: BetaFeedbackSeverity = BetaFeedbackSeverity.MEDIUM
    safe_context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "description")
    @classmethod
    def sanitize_fields(cls, value: str) -> str:
        return sanitize_text(value).strip()


class BetaFeedbackAdminFilters(BaseModel):
    project_id: UUID | None = None
    source: BetaFeedbackSource | None = None
    severity: BetaFeedbackSeverity | None = None
    status: BetaFeedbackStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=200, ge=1, le=500)
