"""Onboarding API schemas (Phase AI.86)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.contracts import OnboardingStep


class OnboardingStepStatus(BaseModel):
    step: OnboardingStep
    completed: bool
    derived: bool = True
    manual_allowed: bool = False


class OnboardingStatusResponse(BaseModel):
    project_id: str | None = None
    steps: list[OnboardingStepStatus] = Field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0


class OnboardingCompleteStepRequest(BaseModel):
    step: OnboardingStep
