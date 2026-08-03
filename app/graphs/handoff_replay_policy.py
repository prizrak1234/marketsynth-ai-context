"""Eligibility rules for handoff child replay (single and batch)."""

from __future__ import annotations

from app.db.models.agent_run import AgentRunTable
from app.graphs.handoff import is_handoff_child_run
from app.graphs.handoff_worker_state import get_handoff_worker_state
from app.schemas.contracts import AgentRunStatus


def is_handoff_child_batch_replayable(
    run: AgentRunTable,
    *,
    max_attempts: int,
) -> bool:
    metadata = dict(run.run_metadata or {})
    if not is_handoff_child_run(metadata):
        return False
    if run.status in (AgentRunStatus.SUCCEEDED, AgentRunStatus.CANCELLED):
        return False

    worker_state = get_handoff_worker_state(metadata)
    if worker_state.get("dead_lettered"):
        return True
    if run.status == AgentRunStatus.FAILED:
        return True
    attempts = int(worker_state.get("attempts", 0))
    return attempts >= max_attempts


def is_handoff_child_single_replayable(run: AgentRunTable) -> bool:
    metadata = dict(run.run_metadata or {})
    if not is_handoff_child_run(metadata):
        return False
    if run.status in (AgentRunStatus.SUCCEEDED, AgentRunStatus.CANCELLED):
        return False

    worker_state = get_handoff_worker_state(metadata)
    if worker_state.get("dead_lettered"):
        return True
    if run.status in (AgentRunStatus.FAILED, AgentRunStatus.QUEUED):
        return True
    if run.status == AgentRunStatus.RUNNING:
        return False
    return False
