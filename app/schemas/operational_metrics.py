"""Operational metrics API contracts (Phase 3.11)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.repositories.operational_metrics import METRICS_WINDOW_LABEL


class ReviewQueueOperationalMetrics(BaseModel):
    pending_assets: int = 0


class OperationalMetricsRedis(BaseModel):
    available: bool
    queue_depth: int = 0
    dlq_depth: int = 0
    error: str | None = None


class OperationalMetricsResponse(BaseModel):
    project_id: UUID | None = None
    window: str = METRICS_WINDOW_LABEL
    agent_runs: dict[str, int] = Field(default_factory=dict)
    graph_runs: dict[str, int] = Field(default_factory=dict)
    handoff: dict[str, Any] = Field(default_factory=dict)
    outbox: dict[str, Any] = Field(default_factory=dict)
    webhooks: dict[str, Any] = Field(default_factory=dict)
    execution: dict[str, Any] = Field(default_factory=dict)
    replay: dict[str, Any] = Field(default_factory=dict)
    publishing: dict[str, Any] = Field(default_factory=dict)
    campaigns: dict[str, int] = Field(default_factory=dict)
    review_queue: ReviewQueueOperationalMetrics = Field(
        default_factory=ReviewQueueOperationalMetrics,
    )
    redis: OperationalMetricsRedis


class OperationsHealthResponse(BaseModel):
    status: str
    app: str
    database: str
    redis: str
    handoff_scheduler_enabled: bool
    outbox_dispatcher_enabled: bool
    publication_worker_enabled: bool
    graph_version: str
    pending_outbox_count: int
    pending_publication_jobs_count: int = 0
    handoff_queue_known_owners_count: int
    config_warnings_count: int = 0
    config_warnings: list[str] = Field(default_factory=list)
