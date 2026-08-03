"""Marketer orchestrator delegation — planning mode only (Phase AI.27)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.planning import execute_marketer_orchestrator_planning
from app.core.exceptions import ExecutorError, NotFoundError
from app.db.models.agent_run import AgentRunTable
from app.schemas.agent_chat import AgentChatSubagentChainEntry, AgentChatSubagentExecution
from app.schemas.contracts import AgentStatus, AgentType
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService


@dataclass(frozen=True)
class MarketerOrchestratorDelegationResult:
    final_run: AgentRunTable
    subagent_chain: list[AgentChatSubagentChainEntry] | None
    subagent_execution: AgentChatSubagentExecution | None


def planning_mode_delegation_result(
    final_run: AgentRunTable,
) -> MarketerOrchestratorDelegationResult:
    """Delegation result for planning-only mode (no subagent execution)."""
    return MarketerOrchestratorDelegationResult(
        final_run=final_run,
        subagent_chain=None,
        subagent_execution=None,
    )


def _message_from_input_payload(input_payload: dict[str, Any]) -> str:
    prompt = input_payload.get("prompt")
    if isinstance(prompt, str):
        return prompt
    agent_chat = input_payload.get("agent_chat")
    if isinstance(agent_chat, dict):
        nested = agent_chat.get("prompt")
        if isinstance(nested, str):
            return nested
    return ""


async def execute_marketer_orchestrator_delegation(
    session: AsyncSession,
    *,
    orchestrator_parent_run: AgentRunTable,
    input_payload: dict[str, Any],
    owner_id: UUID,
) -> MarketerOrchestratorDelegationResult:
    """
    Build a MarketingExecutionPlan on the orchestrator run.

    No sub-agent child runs, tools, or auto-delegation in AI.27.
    """
    return await execute_marketer_orchestrator_planning(
        session,
        orchestrator_parent_run=orchestrator_parent_run,
        input_payload=input_payload,
        owner_id=owner_id,
    )


async def resolve_project_orchestrator_agent_id(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
) -> UUID:
    agents = await AgentService(session).list_agents(owner_id, project_id=project_id)
    matching = [
        agent
        for agent in agents
        if agent.type == AgentType.ORCHESTRATOR and agent.status != AgentStatus.ARCHIVED
    ]
    active = [agent for agent in matching if agent.status == AgentStatus.ACTIVE]
    pool = active or matching
    if not pool:
        raise NotFoundError("No orchestrator agent in project")
    return pool[0].id
