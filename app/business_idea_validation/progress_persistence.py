"""Persist BIV run progress to durable storage during pipeline execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID

from app.business_idea_validation.run_progress import BivRunProgressTracker
from app.schemas.contracts import BivPipelineStage, BivRunProgress


PersistCallback = Callable[[BivRunProgress], Awaitable[None]]


def schedule_persist(callback: PersistCallback, snapshot: BivRunProgress) -> None:
    """Fire-and-forget persist while sync pipeline code runs inside async service."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(callback(snapshot))


class PersistingBivRunProgressTracker(BivRunProgressTracker):
    """Progress tracker that schedules async persist on each state change."""

    def __init__(
        self,
        *,
        run_id: UUID,
        correlation_id: str,
        started_at: datetime | None = None,
        on_persist: PersistCallback | None = None,
    ) -> None:
        super().__init__(run_id=run_id, correlation_id=correlation_id, started_at=started_at)
        self._on_persist = on_persist

    def advance(self, stage: BivPipelineStage) -> None:
        super().advance(stage)
        if self._on_persist is not None:
            schedule_persist(self._on_persist, self.snapshot())

    def mark_failed(self, *, safe_message: str, error_code: str) -> None:
        super().mark_failed(safe_message=safe_message, error_code=error_code)
        if self._on_persist is not None:
            schedule_persist(self._on_persist, self.snapshot())
