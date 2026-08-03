"""Agent run workflow summary API models (Phase 5.7)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowAssetSummary(BaseModel):
    id: UUID
    title: str
    type: str
    status: str
    agent_run_id: UUID | None = None
    source_asset_id: UUID | None = None
    metadata_purpose: str | None = None
    quality_score: float | None = None


class WorkflowChildRunSummary(BaseModel):
    id: UUID
    agent_type: str
    status: str
    created_assets: list[WorkflowAssetSummary] = Field(default_factory=list)


class AgentRunWorkflowSummary(BaseModel):
    parent_run_id: UUID
    status: str
    handoff: dict[str, Any] = Field(default_factory=dict)
    child_runs: list[WorkflowChildRunSummary] = Field(default_factory=list)
    related_assets: list[WorkflowAssetSummary] = Field(default_factory=list)
