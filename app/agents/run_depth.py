"""AgentRun hierarchy depth guards (Phase AI.15)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.models.agent_run import AgentRunTable

MAX_AGENT_RUN_DEPTH = 2


async def compute_agent_run_depth(
    session: AsyncSession,
    run: AgentRunTable,
    owner_id: UUID,
) -> int:
    """Root run depth = 0; each parent link adds one."""
    from app.services.agent_runs import AgentRunService

    depth = 0
    current_parent_id = run.parent_agent_run_id
    agent_runs = AgentRunService(session)
    while current_parent_id is not None:
        depth += 1
        if depth > MAX_AGENT_RUN_DEPTH:
            break
        parent = await agent_runs.get_run(owner_id, current_parent_id)
        if parent is None:
            break
        current_parent_id = parent.parent_agent_run_id
    return depth


async def ensure_child_depth_allowed(
    session: AsyncSession,
    parent_run: AgentRunTable,
    owner_id: UUID,
) -> None:
    parent_depth = await compute_agent_run_depth(session, parent_run, owner_id)
    if parent_depth >= MAX_AGENT_RUN_DEPTH:
        raise InvalidStateError("Maximum agent run depth exceeded")
