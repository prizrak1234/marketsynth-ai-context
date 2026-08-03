"""Replay dead-lettered handoff child agent runs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.agent_run import AgentRunTable
from app.graphs.handoff_replay_policy import (
    is_handoff_child_batch_replayable,
    is_handoff_child_single_replayable,
)
from app.graphs.handoff_sync import merge_handoff_child_requeued
from app.graphs.handoff_worker_state import reset_handoff_worker_for_replay
from app.queues.handoff_child_queue import HandoffChildQueue
from app.schemas.contracts import AgentRunStatus
from app.schemas.operational_batch import HandoffReplayBatchResponse
from app.services.agent_runs import AgentRunService
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class HandoffReplayService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._agent_runs = AgentRunService(session)
        self._queue = HandoffChildQueue()

    async def replay_child_run(
        self,
        owner_id: UUID,
        child_run_id: UUID,
    ) -> dict | None:
        child = await self._agent_runs.get_run(owner_id, child_run_id)
        if child is None or not is_handoff_child_single_replayable(child):
            return None
        requeued = await self._requeue_child(owner_id, child)
        if not requeued:
            return None
        return {
            "child_run_id": str(child_run_id),
            "status": AgentRunStatus.QUEUED.value,
            "replayed": True,
        }

    async def replay_batch(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        limit: int,
    ) -> HandoffReplayBatchResponse | None:
        project = await ProjectService(self._session).get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None

        settings = get_settings()
        runs = await self._agent_runs.list_runs(
            owner_id,
            project_id=project_id,
            limit=500,
        )
        candidates = [
            run
            for run in runs
            if is_handoff_child_batch_replayable(
                run,
                max_attempts=settings.graph_handoff_max_attempts,
            )
        ]
        batch = candidates[:limit]
        matched_count = len(batch)
        requeued_count = 0
        skipped_count = 0

        for run in batch:
            if await self._requeue_child(owner_id, run):
                requeued_count += 1
            else:
                skipped_count += 1

        return HandoffReplayBatchResponse(
            matched_count=matched_count,
            requeued_count=requeued_count,
            skipped_count=skipped_count,
        )

    async def _requeue_child(self, owner_id: UUID, child: AgentRunTable) -> bool:
        child_run_id = child.id
        parent_raw = dict(child.run_metadata or {}).get("parent_agent_run_id")
        metadata = reset_handoff_worker_for_replay(dict(child.run_metadata or {}))
        async with transactional(self._session):
            await self._agent_runs.patch_run_metadata(owner_id, child_run_id, metadata)
            requeued = await self._agent_runs.requeue_for_handoff_retry(owner_id, child_run_id)
        if requeued is None:
            return False

        await self._queue.enqueue(owner_id, child_run_id)
        if isinstance(parent_raw, str) and parent_raw.strip():
            parent_id = UUID(parent_raw.strip())
            parent = await self._agent_runs.get_run(owner_id, parent_id)
            if parent is not None and isinstance(parent.output_payload, dict):
                merged = merge_handoff_child_requeued(parent.output_payload)
                await self._agent_runs.patch_output_payload(owner_id, parent_id, merged)
        return True
