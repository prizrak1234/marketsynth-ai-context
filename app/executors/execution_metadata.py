"""Stamp execution engine metadata on agent runs (Phase 3.13–3.14)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.db.base import utc_now
from app.db.models.agent_run import AgentRunTable
from app.executors.engine_resolver import ExecutionEngine
from app.executors.execution_guard import CLAIM_SOURCE_EXECUTE, get_stored_idempotency_key
from app.services.agent_runs import AgentRunService


def build_execution_block(
    engine: ExecutionEngine,
    *,
    graph_version: str | None = None,
    idempotency_key: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    claim_source: str = CLAIM_SOURCE_EXECUTE,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "engine": engine,
        "claim_source": claim_source,
    }
    if engine == "langgraph":
        block["graph_version"] = graph_version or get_settings().graph_version
    if idempotency_key:
        block["idempotency_key"] = idempotency_key
    if started_at:
        block["started_at"] = started_at
    if finished_at:
        block["finished_at"] = finished_at
    return block


def merge_execution_into_payload(
    output_payload: dict[str, Any] | None,
    engine: ExecutionEngine,
    *,
    idempotency_key: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    claim_source: str = CLAIM_SOURCE_EXECUTE,
) -> dict[str, Any]:
    merged = dict(output_payload or {})
    existing = merged.get("execution")
    key = idempotency_key
    if not key and isinstance(existing, dict):
        stored = existing.get("idempotency_key")
        if isinstance(stored, str) and stored.strip():
            key = stored.strip()
    merged["execution"] = build_execution_block(
        engine,
        idempotency_key=key,
        started_at=started_at
        or (existing.get("started_at") if isinstance(existing, dict) else None),
        finished_at=finished_at,
        claim_source=claim_source,
    )
    return merged


def get_execution_engine_from_run(run: AgentRunTable) -> ExecutionEngine | None:
    output = dict(run.output_payload or {})
    execution = output.get("execution")
    if isinstance(execution, dict):
        engine = execution.get("engine")
        normalized = str(engine).strip().lower() if engine is not None else None
        if normalized in ("classic", "langgraph"):
            return normalized

    metadata = dict(run.run_metadata or {})
    execution_meta = metadata.get("execution")
    if isinstance(execution_meta, dict):
        engine = execution_meta.get("engine")
        normalized = str(engine).strip().lower() if engine is not None else None
        if normalized in ("classic", "langgraph"):
            return normalized

    legacy = output.get("execution_engine")
    if legacy == "langgraph":
        return "langgraph"
    return None


async def stamp_execution_on_run(
    agent_runs: AgentRunService,
    owner_id: UUID,
    run_id: UUID,
    engine: ExecutionEngine,
    *,
    idempotency_key: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    claim_source: str = CLAIM_SOURCE_EXECUTE,
) -> AgentRunTable | None:
    run = await agent_runs.get_run(owner_id, run_id)
    if run is None:
        return None

    resolved_key = idempotency_key or get_stored_idempotency_key(run)
    resolved_started = started_at
    if not resolved_started and run.started_at:
        resolved_started = run.started_at.isoformat()
    resolved_finished = finished_at
    if not resolved_finished and run.finished_at:
        resolved_finished = run.finished_at.isoformat()
    elif not resolved_finished and run.status.value in ("succeeded", "failed", "cancelled"):
        resolved_finished = utc_now().isoformat()

    if isinstance(run.output_payload, dict):
        merged = merge_execution_into_payload(
            run.output_payload,
            engine,
            idempotency_key=resolved_key,
            started_at=resolved_started,
            finished_at=resolved_finished,
            claim_source=claim_source,
        )
        return await agent_runs.patch_output_payload(owner_id, run_id, merged)

    metadata = dict(run.run_metadata or {})
    metadata["execution"] = build_execution_block(
        engine,
        idempotency_key=resolved_key,
        started_at=resolved_started,
        finished_at=resolved_finished,
        claim_source=claim_source,
    )
    return await agent_runs.patch_run_metadata(owner_id, run_id, metadata)
