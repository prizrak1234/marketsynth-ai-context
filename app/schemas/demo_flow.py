"""E2E demo flow API schemas (Phase AI.81–AI.83)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DemoFlowStatusResponse(BaseModel):
    marketing_plan_status: str | None = None
    execution_run_status: str | None = None
    completed_specialists: list[str] = Field(default_factory=list)
    content_asset_status: str | None = None
    media_brief_status: str | None = None
    media_asset_status: str | None = None
    publication_package_status: str | None = None
    publication_job_status: str | None = None
    publication_schedule_status: str | None = None
    next_available_action: str | None = None
    resource_links: dict[str, str] = Field(default_factory=dict)
    failed_step: str | None = None
    blocking_reason: str | None = None
    last_error_code: str | None = None
    suggested_next_action: str | None = None


class ProvenanceNodeSummary(BaseModel):
    id: UUID
    status: str | None = None
    safe_summary: str | None = None


class DemoFlowResetResponse(BaseModel):
    project_id: UUID
    cleared: bool
    removed_counts: dict[str, int] = Field(default_factory=dict)


class ContentProductionProvenanceResponse(BaseModel):
    publication_package_job_id: UUID
    marketing_plan: ProvenanceNodeSummary | None = None
    execution_run: ProvenanceNodeSummary | None = None
    copywriter_output: ProvenanceNodeSummary | None = None
    content_asset: ProvenanceNodeSummary | None = None
    media_brief: ProvenanceNodeSummary | None = None
    media_asset: ProvenanceNodeSummary | None = None
    publication_package: ProvenanceNodeSummary | None = None
    publication_package_job: ProvenanceNodeSummary | None = None
    publishing_channel: ProvenanceNodeSummary | None = None
    source_scenario_id: str | None = None
    source_scenario_name: str | None = None
    source_wizard_run_id: str | None = None
    source_campaign_id: str | None = None
