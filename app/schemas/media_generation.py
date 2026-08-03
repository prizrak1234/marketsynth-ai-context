"""Media generation API request bodies (Phase AI.56)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateMediaGenerationJobBody(BaseModel):
    provider: str = Field(default="mock", max_length=32)
    media_type: str = Field(default="image", max_length=32)
