"""Handoff child worker attempt tracking in agent run metadata."""

from __future__ import annotations

from typing import Any

from app.db.base import utc_now
from app.db.models.agent_run import AgentRunTable
from app.queues.handoff_dead_letter_queue import sanitize_handoff_worker_error

HANDOFF_WORKER_METADATA_KEY = "handoff_worker"


def get_handoff_worker_state(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    raw = metadata.get(HANDOFF_WORKER_METADATA_KEY)
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


def merge_handoff_worker_metadata(
    metadata: dict[str, Any] | None,
    worker_state: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(metadata or {})
    merged[HANDOFF_WORKER_METADATA_KEY] = worker_state
    return merged


def record_handoff_worker_attempt(
    metadata: dict[str, Any] | None,
    *,
    last_error: str,
) -> dict[str, Any]:
    state = get_handoff_worker_state(metadata)
    attempts = int(state.get("attempts", 0)) + 1
    worker_state = {
        "attempts": attempts,
        "last_attempt_at": utc_now().isoformat(),
        "last_error": sanitize_handoff_worker_error(last_error),
        "dead_lettered": bool(state.get("dead_lettered", False)),
    }
    return merge_handoff_worker_metadata(metadata, worker_state)


def mark_handoff_worker_dead_lettered(metadata: dict[str, Any] | None) -> dict[str, Any]:
    state = get_handoff_worker_state(metadata)
    state["dead_lettered"] = True
    state.setdefault("attempts", 0)
    return merge_handoff_worker_metadata(metadata, state)


def reset_handoff_worker_for_replay(metadata: dict[str, Any] | None) -> dict[str, Any]:
    return merge_handoff_worker_metadata(
        metadata,
        {
            "attempts": 0,
            "last_attempt_at": None,
            "last_error": None,
            "dead_lettered": False,
        },
    )


def is_handoff_worker_eligible(run: AgentRunTable, *, max_attempts: int) -> bool:
    state = get_handoff_worker_state(dict(run.run_metadata or {}))
    if state.get("dead_lettered"):
        return False
    attempts = int(state.get("attempts", 0))
    return not attempts >= max_attempts
