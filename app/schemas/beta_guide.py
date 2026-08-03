"""Read-only beta tester guide (Phase AI.97)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BetaGuideStep(BaseModel):
    key: str
    label: str
    hint: str | None = None


class BetaGuideResponse(BaseModel):
    current_phase: str = "closed_beta_mvp"
    what_to_test: list[str] = Field(default_factory=list)
    expected_path: list[BetaGuideStep] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    feedback_instructions: str = ""
