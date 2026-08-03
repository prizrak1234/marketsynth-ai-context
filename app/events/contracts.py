"""Event payload contracts — mirrors app.schemas.contracts event types."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

HANDOFF_CHILD_STATUS_DEAD_LETTERED = "dead_lettered"


class HandoffParentSyncedEventPayload(BaseModel):
    parent_run_id: str
    child_run_id: str
    child_run_status: str
    child_run_executed: bool
    dead_lettered: bool
    synced_at: str


def build_handoff_parent_synced_payload(
    *,
    parent_run_id: str,
    child_run_id: str,
    child_run_status: str,
    child_run_executed: bool,
    dead_lettered: bool,
    synced_at: str,
) -> dict[str, Any]:
    payload = HandoffParentSyncedEventPayload(
        parent_run_id=parent_run_id,
        child_run_id=child_run_id,
        child_run_status=child_run_status,
        child_run_executed=child_run_executed,
        dead_lettered=dead_lettered,
        synced_at=synced_at,
    )
    return payload.model_dump()
