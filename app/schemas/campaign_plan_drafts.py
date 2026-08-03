"""Campaign plan draft API schemas (Phase 10.1)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignPlanDraftCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    plan_payload: dict[str, Any]
    source_agent_run_id: UUID | None = None


class PlanDraftGenerateAssetsResponse(BaseModel):
    created_count: int = Field(ge=0)
    asset_ids: list[UUID]
    already_generated: bool = False
