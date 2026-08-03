"""In-memory graph checkpoints — DB persistence deferred to a later phase."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.db.base import utc_now
from app.graphs.contracts import assert_no_graph_state_secrets


@dataclass(frozen=True)
class GraphCheckpoint:
    trace_id: str
    agent_run_id: UUID
    node_name: str
    state_snapshot: dict[str, Any]
    created_at: datetime = field(default_factory=utc_now)


class GraphCheckpointStore(Protocol):
    async def save(self, checkpoint: GraphCheckpoint) -> None: ...

    async def list_for_run(
        self,
        agent_run_id: UUID,
        *,
        trace_id: str | None = None,
    ) -> list[GraphCheckpoint]: ...


class InMemoryGraphCheckpointStore:
    """Process-local checkpoint store for tests and graph dry-run tracing."""

    def __init__(self) -> None:
        self._checkpoints: list[GraphCheckpoint] = []

    async def save(self, checkpoint: GraphCheckpoint) -> None:
        assert_no_graph_state_secrets(checkpoint.state_snapshot)
        self._checkpoints.append(checkpoint)

    async def list_for_run(
        self,
        agent_run_id: UUID,
        *,
        trace_id: str | None = None,
    ) -> list[GraphCheckpoint]:
        rows = [
            row
            for row in self._checkpoints
            if row.agent_run_id == agent_run_id
        ]
        if trace_id is not None:
            rows = [row for row in rows if row.trace_id == trace_id]
        return sorted(rows, key=lambda row: row.created_at)

    def clear(self) -> None:
        self._checkpoints.clear()
