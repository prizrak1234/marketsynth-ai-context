"""Background scheduler for event outbox → project webhook delivery."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.events.dispatcher import EventOutboxDispatcher

log = get_logger(__name__)


class OutboxDispatcherScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        settings = get_settings()
        if not settings.event_outbox_dispatcher_enabled:
            return
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name="outbox-dispatcher-scheduler")
        log.info(
            "outbox_dispatcher_scheduler_started",
            interval_seconds=settings.event_outbox_dispatcher_interval_seconds,
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        log.info("outbox_dispatcher_scheduler_stopped")

    async def _run_loop(self) -> None:
        settings = get_settings()
        interval = settings.event_outbox_dispatcher_interval_seconds
        while not self._stop.is_set():
            try:
                await self.run_once()
            except Exception:
                log.exception("outbox_dispatcher_scheduler_tick_failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
                break
            except TimeoutError:
                continue

    async def run_once(self) -> dict[str, int]:
        factory = get_session_factory()
        async with factory() as session:
            batch = await EventOutboxDispatcher(session).dispatch_batch()
        return {
            "dispatched": batch.dispatched_count,
            "skipped": batch.skipped_count,
            "failed": batch.failed_count,
        }


_outbox_dispatcher_scheduler: OutboxDispatcherScheduler | None = None


def get_outbox_dispatcher_scheduler() -> OutboxDispatcherScheduler:
    global _outbox_dispatcher_scheduler
    if _outbox_dispatcher_scheduler is None:
        _outbox_dispatcher_scheduler = OutboxDispatcherScheduler()
    return _outbox_dispatcher_scheduler


def reset_outbox_dispatcher_scheduler() -> None:
    global _outbox_dispatcher_scheduler
    _outbox_dispatcher_scheduler = None
