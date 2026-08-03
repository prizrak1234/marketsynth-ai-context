"""In-process dispatcher for durable BIV research runs (RUNTIME-01A)."""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.services.business_idea_validation_service import BusinessIdeaValidationService
from app.services.transaction import transactional

log = get_logger(__name__)

INTERRUPTED_ERROR_CODE = "research_execution_interrupted"


class BivRunDispatcher:
    """DB-backed queue dispatcher; asyncio tasks are execution-only."""

    def __init__(self) -> None:
        self._in_flight: set[UUID] = set()
        self._lock = asyncio.Lock()

    async def dispatch(self, run_id: UUID) -> None:
        settings = get_settings()
        if not settings.biv_run_dispatcher_enabled:
            return
        async with self._lock:
            if run_id in self._in_flight:
                return
            self._in_flight.add(run_id)
        asyncio.create_task(self._run_and_release(run_id), name=f"biv-run-{run_id}")

    async def _run_and_release(self, run_id: UUID) -> None:
        try:
            await self._execute_run(run_id)
        except Exception:
            log.exception(
                "biv_run_dispatcher_task_failed",
                run_id=str(run_id),
            )
        finally:
            async with self._lock:
                self._in_flight.discard(run_id)

    async def _execute_run(self, run_id: UUID) -> None:
        settings = get_settings()
        factory = get_session_factory()
        async with factory() as session:
            svc = BusinessIdeaValidationService(session, settings)
            claimed = await svc.try_claim_queued_run(run_id)
            if not claimed:
                return
        async with factory() as session:
            svc = BusinessIdeaValidationService(session, settings)
            await svc.execute_claimed_run(run_id)

    async def recover_on_startup(self) -> dict[str, int]:
        settings = get_settings()
        if not settings.biv_run_dispatcher_enabled:
            return {"queued_redispatched": 0, "stale_interrupted": 0}

        from datetime import timedelta

        from app.db.base import utc_now
        from app.db.repositories.business_idea_validation_runs import (
            BusinessIdeaValidationRunRepository,
        )
        from app.schemas.contracts import BusinessIdeaValidationRunStatus

        factory = get_session_factory()
        stale_before = utc_now() - timedelta(seconds=settings.biv_run_stale_seconds)
        queued_ids: list[UUID] = []
        stale_ids: list[UUID] = []

        async with factory() as session:
            repo = BusinessIdeaValidationRunRepository(session)
            stale_ids = await repo.list_stale_running_run_ids(stale_before)
            for stale_id in stale_ids:
                row = await repo.get_by_id(stale_id)
                if row is None:
                    continue
                row.status = BusinessIdeaValidationRunStatus.FAILED
                row.error_code = INTERRUPTED_ERROR_CODE
                row.safe_error_message = BusinessIdeaValidationService.interrupted_safe_message()
                now = utc_now()
                row.finished_at = now
                row.updated_at = now
                if row.progress_json:
                    progress = dict(row.progress_json)
                    progress["state"] = BusinessIdeaValidationRunStatus.FAILED.value
                    progress["failure"] = {
                        "error_code": INTERRUPTED_ERROR_CODE,
                        "safe_message": row.safe_error_message,
                    }
                    row.progress_json = progress
                async with transactional(session):
                    await repo.update(row)
                log.warning(
                    "biv_run_stale_interrupted",
                    run_id=str(stale_id),
                    project_id=str(row.project_id),
                    error_code=INTERRUPTED_ERROR_CODE,
                )

            queued_ids = await repo.list_queued_run_ids()

        for run_id in queued_ids:
            await self.dispatch(run_id)

        if queued_ids or stale_ids:
            log.info(
                "biv_run_startup_recovery",
                queued_redispatched=len(queued_ids),
                stale_interrupted=len(stale_ids),
            )
        return {
            "queued_redispatched": len(queued_ids),
            "stale_interrupted": len(stale_ids),
        }


_biv_run_dispatcher: BivRunDispatcher | None = None


def get_biv_run_dispatcher() -> BivRunDispatcher:
    global _biv_run_dispatcher
    if _biv_run_dispatcher is None:
        _biv_run_dispatcher = BivRunDispatcher()
    return _biv_run_dispatcher


def reset_biv_run_dispatcher() -> None:
    global _biv_run_dispatcher
    _biv_run_dispatcher = None


async def stop_biv_run_dispatcher() -> None:
    dispatcher = get_biv_run_dispatcher()
    pending = list(dispatcher._in_flight)
    if not pending:
        return
    await asyncio.gather(
        *[
            asyncio.create_task(_wait_for_run(dispatcher, run_id))
            for run_id in pending
        ],
        return_exceptions=True,
    )


async def _wait_for_run(dispatcher: BivRunDispatcher, run_id: UUID) -> None:
    for _ in range(600):
        if run_id not in dispatcher._in_flight:
            return
        await asyncio.sleep(0.05)
