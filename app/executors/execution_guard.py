"""Claim and idempotency guards for unified agent run execute (Phase 3.14)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.core.exceptions import InvalidStateError, NotFoundError
from app.db.base import utc_now
from app.db.models.agent_run import AgentRunTable
from app.executors.idempotency import normalize_idempotency_key
from app.schemas.contracts import AgentRunStatus
from app.services.agent_runs import AgentRunService

CLAIM_SOURCE_EXECUTE = "execute_endpoint"
TERMINAL_STATUSES = frozenset(
    {
        AgentRunStatus.SUCCEEDED,
        AgentRunStatus.FAILED,
        AgentRunStatus.CANCELLED,
    },
)


@dataclass(frozen=True)
class ExecutePrepareResult:
    kind: Literal["execute", "cached"]
    run: AgentRunTable
    idempotency_key: str | None
    started_at: str


def get_stored_idempotency_key(run: AgentRunTable) -> str | None:
    metadata = dict(run.run_metadata or {})
    execution_meta = metadata.get("execution")
    if isinstance(execution_meta, dict):
        stored = execution_meta.get("idempotency_key")
        if isinstance(stored, str) and stored.strip():
            return stored.strip()

    output = dict(run.output_payload or {})
    execution_output = output.get("execution")
    if isinstance(execution_output, dict):
        stored = execution_output.get("idempotency_key")
        if isinstance(stored, str) and stored.strip():
            return stored.strip()
    return None


async def _persist_idempotency_key(
    agent_runs: AgentRunService,
    owner_id: UUID,
    run_id: UUID,
    idempotency_key: str,
) -> AgentRunTable | None:
    run = await agent_runs.get_run(owner_id, run_id)
    if run is None:
        return None
    metadata = dict(run.run_metadata or {})
    execution_meta = dict(metadata.get("execution") or {})
    execution_meta["idempotency_key"] = idempotency_key
    metadata["execution"] = execution_meta
    return await agent_runs.patch_run_metadata(owner_id, run_id, metadata)


async def prepare_agent_run_execute(
    agent_runs: AgentRunService,
    owner_id: UUID,
    run_id: UUID,
    *,
    idempotency_key: str | None,
) -> ExecutePrepareResult:
    normalized_key = normalize_idempotency_key(idempotency_key)
    run = await agent_runs.get_run(owner_id, run_id)
    if run is None:
        raise NotFoundError("Agent run not found")

    if run.status == AgentRunStatus.SUCCEEDED:
        if normalized_key is not None:
            stored = get_stored_idempotency_key(run)
            if stored == normalized_key:
                started = run.started_at.isoformat() if run.started_at else None
                return ExecutePrepareResult(
                    kind="cached",
                    run=run,
                    idempotency_key=normalized_key,
                    started_at=started or utc_now().isoformat(),
                )
            if stored is not None:
                raise InvalidStateError("idempotency_key_mismatch")
        raise InvalidStateError("agent_run_already_completed")

    if run.status in TERMINAL_STATUSES:
        raise InvalidStateError(f"agent_run_not_executable:{run.status.value}")

    if run.status == AgentRunStatus.RUNNING:
        raise InvalidStateError("already_running_or_claimed")

    if run.status != AgentRunStatus.QUEUED:
        raise InvalidStateError(f"agent_run_not_executable:{run.status.value}")

    claimed = await agent_runs.claim_queued_run(owner_id, run_id)
    if claimed is None:
        raise InvalidStateError("already_running_or_claimed")

    started_at = claimed.started_at.isoformat() if claimed.started_at else utc_now().isoformat()

    if normalized_key is not None:
        with_key = await _persist_idempotency_key(
            agent_runs,
            owner_id,
            run_id,
            normalized_key,
        )
        if with_key is not None:
            claimed = with_key

    return ExecutePrepareResult(
        kind="execute",
        run=claimed,
        idempotency_key=normalized_key,
        started_at=started_at,
    )
