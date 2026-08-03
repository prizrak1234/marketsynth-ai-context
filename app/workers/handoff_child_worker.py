"""Process queued handoff child agent runs (Phase 3.6+ worker path)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ExecutorError
from app.db.base import utc_now
from app.graphs.handoff import (
    execute_handoff_child_run,
    is_handoff_child_run,
)
from app.graphs.handoff_sync import sync_parent_handoff_after_child
from app.graphs.handoff_worker_state import (
    get_handoff_worker_state,
    is_handoff_worker_eligible,
    mark_handoff_worker_dead_lettered,
    record_handoff_worker_attempt,
)
from app.queues.handoff_child_queue import HandoffChildQueue
from app.queues.handoff_dead_letter_queue import (
    HandoffDeadLetterEntry,
    HandoffDeadLetterQueue,
    sanitize_handoff_worker_error,
)
from app.schemas.contracts import AgentRunStatus
from app.services.agent_runs import AgentRunService


@dataclass(frozen=True)
class HandoffChildWorkerItemResult:
    run_id: UUID
    processed: bool
    skipped: bool
    skip_reason: str | None
    status: str | None
    error: str | None
    parent_synced: bool = False
    requeued: bool = False
    dead_lettered: bool = False


@dataclass(frozen=True)
class HandoffChildWorkerBatchResult:
    requested_limit: int
    processed_count: int
    skipped_count: int
    parent_synced_count: int
    requeued_count: int
    dead_lettered_count: int
    results: list[HandoffChildWorkerItemResult]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "requested_limit": self.requested_limit,
            "processed_count": self.processed_count,
            "skipped_count": self.skipped_count,
            "parent_synced_count": self.parent_synced_count,
            "requeued_count": self.requeued_count,
            "dead_lettered_count": self.dead_lettered_count,
            "results": [
                {
                    "run_id": str(item.run_id),
                    "processed": item.processed,
                    "skipped": item.skipped,
                    "skip_reason": item.skip_reason,
                    "status": item.status,
                    "error": item.error,
                    "parent_synced": item.parent_synced,
                    "requeued": item.requeued,
                    "dead_lettered": item.dead_lettered,
                }
                for item in self.results
            ],
        }


class HandoffChildRunWorker:
    """Drain queued agent runs created by graph handoff delegation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._agent_runs = AgentRunService(session)
        self._queue = HandoffChildQueue()
        self._dlq = HandoffDeadLetterQueue()

    async def list_pending(
        self,
        owner_id: UUID,
        *,
        limit: int | None = None,
    ) -> list:
        settings = get_settings()
        batch_limit = limit if limit is not None else settings.graph_handoff_worker_batch_limit
        if self._queue.is_enabled():
            count = await self._queue.pending_count(owner_id)
            if count > 0:
                scan_limit = max(batch_limit * 5, batch_limit)
                queued = await self._agent_runs.list_runs(
                    owner_id,
                    status=AgentRunStatus.QUEUED,
                    limit=scan_limit,
                )
                max_attempts = settings.graph_handoff_max_attempts
                pending = [
                    row
                    for row in queued
                    if is_handoff_child_run(dict(row.run_metadata or {}))
                    and is_handoff_worker_eligible(row, max_attempts=max_attempts)
                ]
                return pending[:batch_limit]
        return await self._list_pending_from_db(owner_id, limit=batch_limit)

    async def _list_pending_from_db(
        self,
        owner_id: UUID,
        *,
        limit: int,
    ) -> list:
        settings = get_settings()
        scan_limit = max(limit * 5, limit)
        queued = await self._agent_runs.list_runs(
            owner_id,
            status=AgentRunStatus.QUEUED,
            limit=scan_limit,
        )
        pending = [
            row
            for row in queued
            if is_handoff_child_run(dict(row.run_metadata or {}))
            and is_handoff_worker_eligible(row, max_attempts=settings.graph_handoff_max_attempts)
        ]
        return pending[:limit]

    async def _resolve_batch_run_ids(self, owner_id: UUID, batch_limit: int) -> list[UUID]:
        if self._queue.is_enabled():
            queued_ids = await self._queue.dequeue_batch(owner_id, limit=batch_limit)
            if queued_ids:
                return queued_ids
        pending = await self._list_pending_from_db(owner_id, limit=batch_limit)
        return [row.id for row in pending]

    async def _sync_parent_if_terminal(self, owner_id: UUID, run_id: UUID) -> bool:
        child = await self._agent_runs.get_run(owner_id, run_id)
        if child is None:
            return False
        result = await sync_parent_handoff_after_child(
            self._session,
            owner_id=owner_id,
            child_run=child,
            agent_runs=self._agent_runs,
        )
        return result.synced

    async def _handle_execution_failure(
        self,
        owner_id: UUID,
        run_id: UUID,
        exc: BaseException,
    ) -> HandoffChildWorkerItemResult:
        settings = get_settings()
        safe_error = sanitize_handoff_worker_error(str(exc))

        child = await self._agent_runs.get_run(owner_id, run_id)
        if child is None:
            return HandoffChildWorkerItemResult(
                run_id=run_id,
                processed=False,
                skipped=True,
                skip_reason="run_not_found",
                status=None,
                error=None,
            )

        new_metadata = record_handoff_worker_attempt(
            dict(child.run_metadata or {}),
            last_error=safe_error,
        )
        await self._agent_runs.patch_run_metadata(owner_id, run_id, new_metadata)
        attempts = int(get_handoff_worker_state(new_metadata).get("attempts", 0))
        max_attempts = settings.graph_handoff_max_attempts

        if attempts < max_attempts:
            requeued = await self._agent_runs.requeue_for_handoff_retry(owner_id, run_id)
            if requeued is not None:
                await self._queue.enqueue(owner_id, run_id)
            return HandoffChildWorkerItemResult(
                run_id=run_id,
                processed=True,
                skipped=False,
                skip_reason=None,
                status=AgentRunStatus.QUEUED.value,
                error=safe_error,
                requeued=True,
            )

        dlq_metadata = mark_handoff_worker_dead_lettered(new_metadata)
        await self._agent_runs.patch_run_metadata(owner_id, run_id, dlq_metadata)

        parent_raw = dict(child.run_metadata or {}).get("parent_agent_run_id")
        parent_id: UUID | None = None
        if isinstance(parent_raw, str) and parent_raw.strip():
            parent_id = UUID(parent_raw.strip())

        failed_at = utc_now().isoformat()
        if self._dlq.is_enabled():
            await self._dlq.push(
                HandoffDeadLetterEntry(
                    owner_id=owner_id,
                    child_run_id=run_id,
                    parent_run_id=parent_id,
                    reason="handoff_max_attempts_exceeded",
                    attempts=attempts,
                    failed_at=failed_at,
                    last_error=safe_error,
                ),
            )

        child_for_sync = await self._agent_runs.get_run(owner_id, run_id)
        parent_synced = False
        if child_for_sync is not None:
            sync_result = await sync_parent_handoff_after_child(
                self._session,
                owner_id=owner_id,
                child_run=child_for_sync,
                agent_runs=self._agent_runs,
                dead_lettered=True,
            )
            parent_synced = sync_result.synced

        return HandoffChildWorkerItemResult(
            run_id=run_id,
            processed=True,
            skipped=False,
            skip_reason=None,
            status=AgentRunStatus.FAILED.value,
            error=safe_error,
            parent_synced=parent_synced,
            dead_lettered=True,
        )

    async def process_run(
        self,
        owner_id: UUID,
        run_id: UUID,
    ) -> HandoffChildWorkerItemResult:
        settings = get_settings()
        run = await self._agent_runs.get_run(owner_id, run_id)
        if run is None:
            return HandoffChildWorkerItemResult(
                run_id=run_id,
                processed=False,
                skipped=True,
                skip_reason="run_not_found",
                status=None,
                error=None,
            )

        worker_state = get_handoff_worker_state(dict(run.run_metadata or {}))
        if worker_state.get("dead_lettered"):
            return HandoffChildWorkerItemResult(
                run_id=run_id,
                processed=False,
                skipped=True,
                skip_reason="dead_lettered",
                status=run.status.value,
                error=run.error,
            )

        if run.status != AgentRunStatus.QUEUED:
            parent_synced = await self._sync_parent_if_terminal(owner_id, run_id)
            return HandoffChildWorkerItemResult(
                run_id=run_id,
                processed=False,
                skipped=True,
                skip_reason=f"run_status_{run.status.value}",
                status=run.status.value,
                error=run.error,
                parent_synced=parent_synced,
            )
        if not is_handoff_child_run(dict(run.run_metadata or {})):
            return HandoffChildWorkerItemResult(
                run_id=run_id,
                processed=False,
                skipped=True,
                skip_reason="not_handoff_child_run",
                status=run.status.value,
                error=None,
            )
        if not is_handoff_worker_eligible(run, max_attempts=settings.graph_handoff_max_attempts):
            return HandoffChildWorkerItemResult(
                run_id=run_id,
                processed=False,
                skipped=True,
                skip_reason="max_attempts_exceeded",
                status=run.status.value,
                error=run.error,
            )

        try:
            finished = await execute_handoff_child_run(
                self._session,
                owner_id=owner_id,
                run_id=run_id,
                agent_runs=self._agent_runs,
            )
            sync_result = await sync_parent_handoff_after_child(
                self._session,
                owner_id=owner_id,
                child_run=finished,
                agent_runs=self._agent_runs,
            )
            return HandoffChildWorkerItemResult(
                run_id=run_id,
                processed=True,
                skipped=False,
                skip_reason=None,
                status=finished.status.value,
                error=finished.error,
                parent_synced=sync_result.synced,
            )
        except (ExecutorError, Exception) as exc:
            return await self._handle_execution_failure(owner_id, run_id, exc)

    async def process_batch(
        self,
        owner_id: UUID,
        *,
        limit: int | None = None,
    ) -> HandoffChildWorkerBatchResult:
        settings = get_settings()
        batch_limit = limit if limit is not None else settings.graph_handoff_worker_batch_limit
        run_ids = await self._resolve_batch_run_ids(owner_id, batch_limit)

        results: list[HandoffChildWorkerItemResult] = []
        processed_count = 0
        skipped_count = 0
        parent_synced_count = 0
        requeued_count = 0
        dead_lettered_count = 0

        for run_id in run_ids:
            item = await self.process_run(owner_id, run_id)
            results.append(item)
            if item.skipped:
                skipped_count += 1
            elif item.processed:
                processed_count += 1
            if item.parent_synced:
                parent_synced_count += 1
            if item.requeued:
                requeued_count += 1
            if item.dead_lettered:
                dead_lettered_count += 1

        return HandoffChildWorkerBatchResult(
            requested_limit=batch_limit,
            processed_count=processed_count,
            skipped_count=skipped_count,
            parent_synced_count=parent_synced_count,
            requeued_count=requeued_count,
            dead_lettered_count=dead_lettered_count,
            results=results,
        )
