"""CWF.1 — backend-driven BIV run progress (single source of truth)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.db.base import utc_now
from app.schemas.contracts import (
    BivPipelineStage,
    BivRunProgress,
    BivRunProgressFailure,
    BusinessIdeaValidationRunStatus,
)

_STAGE_ORDER: tuple[BivPipelineStage, ...] = (
    BivPipelineStage.NORMALIZING_INPUT,
    BivPipelineStage.DECOMPOSING_QUERIES,
    BivPipelineStage.SEARCHING_DIRECT,
    BivPipelineStage.SEARCHING_INDIRECT,
    BivPipelineStage.SEARCHING_INTERNATIONAL,
    BivPipelineStage.SEARCHING_LOCAL,
    BivPipelineStage.SEARCHING_ADJACENT,
    BivPipelineStage.VALIDATING_SOURCES,
    BivPipelineStage.EXTRACTING_EVIDENCE,
    BivPipelineStage.SYNTHESIZING_FINDINGS,
    BivPipelineStage.CALCULATING_CONFIDENCE,
    BivPipelineStage.CALCULATING_COVERAGE,
    BivPipelineStage.GENERATING_VERDICT,
    BivPipelineStage.BUILDING_REPORT,
    BivPipelineStage.COMPLETED,
)

_STAGE_INDEX = {stage: idx for idx, stage in enumerate(_STAGE_ORDER)}


class BivRunProgressTracker:
    """In-memory progress; persisted to run.progress_json by service layer."""

    def __init__(
        self,
        *,
        run_id: UUID,
        correlation_id: str,
        started_at: datetime | None = None,
    ) -> None:
        self._run_id = run_id
        self._correlation_id = correlation_id
        self._started_at = started_at or utc_now()
        self._updated_at = self._started_at
        self._current = BivPipelineStage.NORMALIZING_INPUT
        self._completed: list[BivPipelineStage] = []
        self._failure: BivRunProgressFailure | None = None
        self._state = BusinessIdeaValidationRunStatus.RUNNING

    def advance(self, stage: BivPipelineStage) -> None:
        if stage in _STAGE_INDEX and self._current in _STAGE_INDEX:
            current_idx = _STAGE_INDEX[self._current]
            target_idx = _STAGE_INDEX[stage]
            for s in _STAGE_ORDER[current_idx:target_idx]:
                if s not in self._completed:
                    self._completed.append(s)
        self._current = stage
        self._updated_at = utc_now()
        if stage == BivPipelineStage.COMPLETED:
            self._state = BusinessIdeaValidationRunStatus.SUCCEEDED

    def mark_failed(self, *, safe_message: str, error_code: str) -> None:
        self._failure = BivRunProgressFailure(
            error_code=error_code,
            safe_message=safe_message,
        )
        self._state = BusinessIdeaValidationRunStatus.FAILED
        self._updated_at = utc_now()

    @property
    def progress_percent(self) -> int:
        if self._current == BivPipelineStage.COMPLETED:
            return 100
        idx = _STAGE_INDEX.get(self._current, 0)
        total = max(len(_STAGE_ORDER) - 1, 1)
        return min(99, int((idx / total) * 100))

    def snapshot(self) -> BivRunProgress:
        return BivRunProgress(
            run_id=self._run_id,
            state=self._state,
            current_stage=self._current,
            completed_stages=list(self._completed),
            started_at=self._started_at,
            updated_at=self._updated_at,
            progress_percent=self.progress_percent,
            failure=self._failure,
            correlation_id=self._correlation_id,
        )
