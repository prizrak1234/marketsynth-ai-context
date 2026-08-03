"""Sequential marketer sub-agent execution (Phase AI.11–AI.14)."""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.registry import get_subagent
from app.agents.run_depth import ensure_child_depth_allowed
from app.core.exceptions import ExecutorError, InvalidStateError, NotFoundError
from app.db.models.agent_run import AgentRunTable
from app.executors.agent_run_coordinator import AgentRunCoordinator
from app.schemas.contracts import AgentRunStatus, AgentStatus, AgentType
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService

SUBAGENT_EXECUTION_SOURCE = "subagent_execution"
SUBAGENT_EXECUTION_METADATA_KEY = "subagent_execution"
_MAX_CHILDREN_PER_PARENT = 1

_SUPPORTED_SUBAGENTS: frozenset[MarketerSubAgentType] = frozenset(
    {
        MarketerSubAgentType.COPYWRITER,
        MarketerSubAgentType.RESEARCHER,
        MarketerSubAgentType.STRATEGIST,
    },
)


def build_subagent_child_input_payload(
    *,
    parent_run: AgentRunTable,
    input_payload: dict[str, Any],
    previous_child_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    child_payload = copy.deepcopy(input_payload)
    agent_chat = child_payload.get("agent_chat")
    if isinstance(agent_chat, dict):
        agent_chat = dict(agent_chat)
        agent_chat.pop("subagent_routing", None)
        child_payload["agent_chat"] = agent_chat
    child_payload["parent_agent_run_id"] = str(parent_run.id)
    child_payload["source"] = SUBAGENT_EXECUTION_SOURCE
    if previous_child_output is not None:
        child_payload["previous_child_output"] = previous_child_output
    return child_payload


def build_subagent_child_metadata(
    *,
    parent_run: AgentRunTable,
    subagent_type: MarketerSubAgentType,
) -> dict[str, Any]:
    metadata = dict(parent_run.run_metadata or {})
    metadata[SUBAGENT_EXECUTION_METADATA_KEY] = {
        "subagent": subagent_type.value,
        "parent_agent_run_id": str(parent_run.id),
        "source": SUBAGENT_EXECUTION_SOURCE,
    }
    return metadata


async def resolve_subagent_agent_id(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
    subagent_type: MarketerSubAgentType,
) -> UUID:
    profile = get_subagent(subagent_type)
    agents = await AgentService(session).list_agents(owner_id, project_id=project_id)
    matching = [
        agent
        for agent in agents
        if agent.type == profile.mapped_agent_type and agent.status != AgentStatus.ARCHIVED
    ]
    active = [agent for agent in matching if agent.status == AgentStatus.ACTIVE]
    pool = active or matching
    if not pool:
        raise NotFoundError(f"No {profile.mapped_agent_type.value} agent available in project")
    return pool[0].id


async def run_subagent_child(
    session: AsyncSession,
    *,
    parent_run: AgentRunTable,
    subagent_type: MarketerSubAgentType,
    input_payload: dict[str, Any],
    owner_id: UUID,
    run_metadata: dict[str, Any] | None = None,
    previous_child_output: dict[str, Any] | None = None,
) -> AgentRunTable:
    """Create and execute one child AgentRun (sibling under orchestrator parent)."""
    if subagent_type not in _SUPPORTED_SUBAGENTS:
        raise InvalidStateError(f"Sub-agent execution not supported for {subagent_type.value}")

    await ensure_child_depth_allowed(session, parent_run, owner_id)

    agent_runs = AgentRunService(session)
    parent_agent = await agent_runs.get_executable_agent(parent_run.agent_id, owner_id)
    if parent_agent.type != AgentType.ORCHESTRATOR:
        raise InvalidStateError("Only orchestrator runs may delegate to sub-agents")

    subagent_agent_id = await resolve_subagent_agent_id(
        session,
        owner_id,
        parent_run.project_id,
        subagent_type,
    )

    child_input = build_subagent_child_input_payload(
        parent_run=parent_run,
        input_payload=input_payload,
        previous_child_output=previous_child_output,
    )
    child_metadata = build_subagent_child_metadata(
        parent_run=parent_run,
        subagent_type=subagent_type,
    )
    if run_metadata:
        child_metadata = {**child_metadata, **run_metadata}

    child_run = await agent_runs.create_run(
        owner_id,
        agent_id=subagent_agent_id,
        task_id=parent_run.task_id,
        input_payload=child_input,
        metadata=child_metadata,
        parent_agent_run_id=parent_run.id,
    )
    if child_run is None:
        raise NotFoundError(f"{subagent_type.value} agent not found")

    final_run, _engine = await AgentRunCoordinator(session).execute_run(
        child_run.id,
        owner_id,
        request_engine="classic",
    )
    if final_run.status != AgentRunStatus.SUCCEEDED:
        raise ExecutorError("Sub-agent temporarily unavailable")
    return final_run


async def execute_subagent(
    session: AsyncSession,
    *,
    parent_run: AgentRunTable,
    subagent_type: MarketerSubAgentType,
    input_payload: dict[str, Any],
    owner_id: UUID,
    run_metadata: dict[str, Any] | None = None,
) -> AgentRunTable:
    """
    Single-child delegation (legacy path). Use chain_execution for multi-step chains.
    """
    agent_runs = AgentRunService(session)
    existing_children = await agent_runs.count_children(parent_run.id, owner_id)
    if existing_children >= _MAX_CHILDREN_PER_PARENT:
        raise InvalidStateError("Parent run already has a sub-agent child")

    return await run_subagent_child(
        session,
        parent_run=parent_run,
        subagent_type=subagent_type,
        input_payload=input_payload,
        owner_id=owner_id,
        run_metadata=run_metadata,
    )


