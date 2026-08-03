"""Beta admin dashboard and QA export schemas (Phase AI.89–AI.94)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BetaAdminDashboardResponse(BaseModel):
    users_total: int = 0
    projects_total: int = 0
    demo_flow_ready_projects: int = 0
    failed_package_jobs: int = 0
    failed_generation_jobs: int = 0
    failed_legacy_publication_jobs: int = 0
    latest_activity_at: datetime | None = None
    window_hours: int = 24


class BetaQaProjectSnapshot(BaseModel):
    project_id: UUID
    project_name: str
    publication_job_status: str | None = None
    failed_step: str | None = None
    last_error_code: str | None = None


class BetaQaDemoCompletionSummary(BaseModel):
    demo_projects_total: int = 0
    publication_queued_count: int = 0
    with_failed_step_count: int = 0


class BetaQaFeedbackCounts(BaseModel):
    open: int = 0
    triaged: int = 0
    resolved: int = 0
    archived: int = 0
    blocker: int = 0
    high: int = 0


class BetaQaFailedJobsSummary(BaseModel):
    failed_package_jobs: int = 0
    failed_generation_jobs: int = 0
    failed_legacy_publication_jobs: int = 0
    window_hours: int = 24


class BetaQaExportResponse(BaseModel):
    generated_at: datetime
    projects: list[BetaQaProjectSnapshot] = Field(default_factory=list)
    demo_completion: BetaQaDemoCompletionSummary = Field(
        default_factory=BetaQaDemoCompletionSummary,
    )
    feedback_counts: BetaQaFeedbackCounts = Field(default_factory=BetaQaFeedbackCounts)
    failed_jobs: BetaQaFailedJobsSummary = Field(default_factory=BetaQaFailedJobsSummary)
