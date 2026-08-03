"""Shared skill input context (Phase AI.228)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SkillInputContext:
    industry: str | None
    offer: str | None
    target_audience: str | None
    geography: str | None
    goal: str | None
    segment_name: str | None
    campaign_id: UUID | None


def parse_skill_context(payload: dict[str, Any]) -> SkillInputContext:
    campaign_raw = payload.get("campaign_id")
    campaign_id = UUID(str(campaign_raw)) if campaign_raw else None
    return SkillInputContext(
        industry=_optional_text(payload.get("industry")),
        offer=_optional_text(payload.get("offer")),
        target_audience=_optional_text(payload.get("target_audience")),
        geography=_optional_text(payload.get("geography")),
        goal=_optional_text(payload.get("goal")),
        segment_name=_optional_text(payload.get("segment_name")),
        campaign_id=campaign_id,
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
