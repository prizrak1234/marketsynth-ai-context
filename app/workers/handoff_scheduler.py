"""Background scheduler that drains Redis handoff child queues (Phase 3.7)."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.queues.handoff_child_queue import HandoffChildQueue
from app.workers.handoff_child_worker import HandoffChildRunWorker

log = get_logger(__name__)


class HandoffChildScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        settings = get_settings()
        if not settings.graph_handoff_scheduler_enabled:
            return
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name="handoff-child-scheduler")
        log.info(
            "handoff_scheduler_started",
            interval_seconds=settings.graph_handoff_scheduler_interval_seconds,
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        log.info("handoff_scheduler_stopped")

    async def _run_loop(self) -> None:
        settings = get_settings()
        interval = settings.graph_handoff_scheduler_interval_seconds
        while not self._stop.is_set():
            try:
                await self.run_once()
            except Exception:
                log.exception("handoff_scheduler_tick_failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
                break
            except TimeoutError:
                continue

    async def run_once(self) -> dict[str, int]:
        settings = get_settings()
        if not settings.graph_handoff_worker_enabled:
            return {"owners": 0, "processed": 0}

        queue = HandoffChildQueue()
        owners = await queue.list_owners_with_pending()
        owner_cap = settings.graph_handoff_scheduler_owner_limit
        batch_limit = settings.graph_handoff_worker_batch_limit
        processed_total = 0

        factory = get_session_factory()
        for owner_id in owners[:owner_cap]:
            async with factory() as session:
                worker = HandoffChildRunWorker(session)
                batch = await worker.process_batch(owner_id, limit=batch_limit)
                processed_total += batch.processed_count

        return {"owners": len(owners[:owner_cap]), "processed": processed_total}


_handoff_scheduler: HandoffChildScheduler | None = None


def get_handoff_scheduler() -> HandoffChildScheduler:
    global _handoff_scheduler
    if _handoff_scheduler is None:
        _handoff_scheduler = HandoffChildScheduler()
    return _handoff_scheduler


def reset_handoff_scheduler() -> None:
    """Reset singleton — for tests only."""
    global _handoff_scheduler
    _handoff_scheduler = None
