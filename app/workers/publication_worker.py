"""Background scheduler for publication job processing (Phase 6.1)."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.services.publication_job_processor import PublicationJobProcessor

log = get_logger(__name__)


class PublicationWorkerScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        settings = get_settings()
        if not settings.publication_worker_enabled:
            return
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name="publication-worker-scheduler")
        log.info(
            "publication_worker_scheduler_started",
            interval_seconds=settings.publication_worker_interval_seconds,
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        log.info("publication_worker_scheduler_stopped")

    async def _run_loop(self) -> None:
        settings = get_settings()
        interval = settings.publication_worker_interval_seconds
        while not self._stop.is_set():
            try:
                await self.run_once()
            except Exception:
                log.exception("publication_worker_scheduler_tick_failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
                break
            except TimeoutError:
                continue

    async def run_once(self) -> dict[str, int]:
        factory = get_session_factory()
        async with factory() as session:
            batch = await PublicationJobProcessor(session).process_batch()
        return batch.to_api_dict()


_publication_worker_scheduler: PublicationWorkerScheduler | None = None


def get_publication_worker_scheduler() -> PublicationWorkerScheduler:
    global _publication_worker_scheduler
    if _publication_worker_scheduler is None:
        _publication_worker_scheduler = PublicationWorkerScheduler()
    return _publication_worker_scheduler


def reset_publication_worker_scheduler() -> None:
    global _publication_worker_scheduler
    _publication_worker_scheduler = None
