"""Sync parent agent run handoff output when a child run completes (Phase 3.7+)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.agent_run import AgentRunTable
from app.events.contracts import HANDOFF_CHILD_STATUS_DEAD_LETTERED
from app.events.outbox import EventOutboxService
from app.graphs.handoff import is_handoff_child_run
from app.schemas.contracts import AgentRunStatus
from app.services.agent_runs import AgentRunService


@dataclass(frozen=True)
class ParentHandoffSyncResult:
    synced: bool
    event_created: bool


def merge_handoff_child_requeued(parent_output: dict[str, Any] | None) -> dict[str, Any]:
    output = dict(parent_output or {})
    handoff = dict(output.get("handoff") or {})
    handoff["child_run_status"] = AgentRunStatus.QUEUED.value
    handoff["child_run_pending_worker"] = True
    handoff["child_run_executed"] = False
    handoff["child_run_error"] = ""
    output["handoff"] = handoff
    return output


def merge_handoff_child_completion(
    parent_output: dict[str, Any] | None,
    *,
    child_status: str,
    child_error: str | None,
    synced_at: str,
    child_run_executed: bool | None = None,
) -> dict[str, Any]:
    output = dict(parent_output or {})
    handoff = dict(output.get("handoff") or {})
    if child_run_executed is None:
        executed = child_status == AgentRunStatus.SUCCEEDED.value
    else:
        executed = child_run_executed
    handoff["child_run_executed"] = executed
    handoff["child_run_pending_worker"] = False
    handoff["child_run_status"] = child_status
    if child_error:
        handoff["child_run_error"] = child_error
    handoff["parent_handoff_synced_at"] = synced_at
    output["handoff"] = handoff
    return output


async def sync_parent_handoff_after_child(
    session: AsyncSession,
    *,
    owner_id: UUID,
    child_run: AgentRunTable,
    agent_runs: AgentRunService | None = None,
    child_status_override: str | None = None,
    dead_lettered: bool = False,
    emit_event: bool = True,
) -> ParentHandoffSyncResult:
    """Patch parent output_payload.handoff when a handoff child reaches a terminal state."""
    terminal_statuses = (
        AgentRunStatus.SUCCEEDED,
        AgentRunStatus.FAILED,
        AgentRunStatus.CANCELLED,
    )
    if not dead_lettered and child_run.status not in terminal_statuses:
        return ParentHandoffSyncResult(synced=False, event_created=False)
    if not is_handoff_child_run(dict(child_run.run_metadata or {})):
        return ParentHandoffSyncResult(synced=False, event_created=False)

    metadata = dict(child_run.run_metadata or {})
    parent_raw = metadata.get("parent_agent_run_id")
    if not isinstance(parent_raw, str) or not parent_raw.strip():
        return ParentHandoffSyncResult(synced=False, event_created=False)

    parent_id = UUID(parent_raw.strip())
    runs = agent_runs or AgentRunService(session)
    parent = await runs.get_run(owner_id, parent_id)
    if parent is None or parent.status != AgentRunStatus.SUCCEEDED:
        return ParentHandoffSyncResult(synced=False, event_created=False)
    if not isinstance(parent.output_payload, dict):
        return ParentHandoffSyncResult(synced=False, event_created=False)
    if "handoff" not in parent.output_payload:
        return ParentHandoffSyncResult(synced=False, event_created=False)

    synced_at = utc_now().isoformat()
    if dead_lettered:
        effective_status = HANDOFF_CHILD_STATUS_DEAD_LETTERED
        child_executed = False
    else:
        effective_status = child_status_override or child_run.status.value
        child_executed = None

    merged = merge_handoff_child_completion(
        parent.output_payload,
        child_status=effective_status,
        child_error=child_run.error,
        synced_at=synced_at,
        child_run_executed=child_executed,
    )
    updated = await runs.patch_output_payload(owner_id, parent_id, merged)
    if updated is None:
        return ParentHandoffSyncResult(synced=False, event_created=False)

    event_created = False
    if emit_event:
        outbox_row = await EventOutboxService(session).append_handoff_parent_synced(
            owner_id=owner_id,
            project_id=parent.project_id,
            parent_run_id=parent_id,
            child_run_id=child_run.id,
            child_run_status=effective_status,
            child_run_executed=merged["handoff"]["child_run_executed"],
            dead_lettered=dead_lettered,
            synced_at=synced_at,
        )
        event_created = outbox_row is not None

    return ParentHandoffSyncResult(synced=True, event_created=event_created)
