"""CWF.1 — persisted run observability (dev/admin diagnostics only)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.db.base import utc_now
from app.schemas.contracts import (
    BivPipelineFailure,
    BivPipelineMetrics,
    BivResearchMode,
    BivRunObservability,
    BivRunStateTransition,
    BivCommercialVerdictKind,
)


class BivRunObservabilityRecorder:
    def __init__(
        self,
        *,
        run_id: UUID,
        correlation_id: str,
        project_id: UUID,
        user_request_id: UUID,
        research_mode: BivResearchMode,
        parent_run_id: UUID | None = None,
    ) -> None:
        self._data = BivRunObservability(
            correlation_id=correlation_id,
            run_id=run_id,
            parent_run_id=parent_run_id,
            research_mode=research_mode,
            project_id=project_id,
            user_request_id=user_request_id,
            started_at=utc_now(),
        )

    def record_transition(self, state: str, *, stage: str | None = None) -> None:
        self._data.state_transitions.append(
            BivRunStateTransition(
                state=state,
                stage=stage,
                at=utc_now(),
            )
        )

    def record_stage_timing(self, stage: str, *, started_at: datetime, finished_at: datetime) -> None:
        self._data.stage_timings[stage] = (finished_at - started_at).total_seconds()

    def increment(self, field: str, amount: int = 1) -> None:
        current = getattr(self._data, field, 0)
        setattr(self._data, field, current + amount)

    def record_provider_error(self, code: str) -> None:
        safe = (code or "provider_error")[:64]
        if safe not in self._data.provider_errors:
            self._data.provider_errors.append(safe)

    def set_final(
        self,
        *,
        confidence: int,
        coverage: int,
        verdict: BivCommercialVerdictKind,
        export_status: str,
        total_latency_ms: int,
    ) -> None:
        self._data.confidence = confidence
        self._data.coverage = coverage
        self._data.verdict = verdict
        self._data.export_status = export_status
        self._data.total_latency_ms = total_latency_ms
        self._data.finished_at = utc_now()

    def set_pipeline_failure(self, failure: BivPipelineFailure) -> None:
        self._data.pipeline_failure = failure

    def attach_pipeline_metrics(self, metrics: BivPipelineMetrics, *, fetch_ledger_count: int = 0) -> None:
        self._data.pipeline_metrics = metrics
        self._data.fetch_ledger_count = fetch_ledger_count

    def snapshot(self) -> BivRunObservability:
        return self._data.model_copy(deep=True)
