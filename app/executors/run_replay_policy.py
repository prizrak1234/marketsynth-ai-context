"""Agent run replay policy — clone failed/cancelled runs only (Phase 3.15)."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidStateError, NotFoundError
from app.db.base import utc_now
from app.db.models.agent import AgentTable
from app.db.models.agent_run import AgentRunTable
from app.schemas.contracts import AgentRunStatus, AgentStatus

REPLAYABLE_STATUSES = frozenset(
    {
        AgentRunStatus.FAILED,
        AgentRunStatus.CANCELLED,
    },
)
REPLAY_REASON_MAX_LENGTH = 256


def normalize_replay_reason(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    if len(cleaned) > REPLAY_REASON_MAX_LENGTH:
        raise InvalidStateError("replay_reason_too_long")
    return cleaned


def validate_replay_source_run(
    run: AgentRunTable,
    agent: AgentTable | None,
) -> None:
    if agent is None:
        raise NotFoundError("Agent not found")
    if agent.status == AgentStatus.ARCHIVED:
        raise InvalidStateError("agent_archived_replay_forbidden")
    if agent.id != run.agent_id:
        raise InvalidStateError("agent_run_agent_mismatch")
    if run.status not in REPLAYABLE_STATUSES:
        raise InvalidStateError(f"agent_run_not_replayable:{run.status.value}")


def build_replay_metadata(
    source_run: AgentRunTable,
    *,
    replay_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "replay": {
            "source_run_id": str(source_run.id),
            "source_status": source_run.status.value,
            "reason": replay_reason,
            "created_at": utc_now().isoformat(),
        },
    }
