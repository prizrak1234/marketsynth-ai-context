"""Normalized API error envelope (Phase AI.88)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    error_code: str
    safe_message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
