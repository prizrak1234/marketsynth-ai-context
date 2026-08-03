"""Programmer delegation execution (Phase AI.16) — single child run, no sub-agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.programmer.contracts import ProgrammerOutputKind
from app.agents.programmer.prompts import TECHNICAL_TASK_DRAFT_TITLE
from app.core.exceptions import ExecutorError, NotFoundError
from app.db.models.agent_run import AgentRunTable
from app.executors.agent_run_coordinator import AgentRunCoordinator
from app.schemas.contracts import AgentRunStatus, AgentStatus, AgentType
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService

PROGRAMMER_DELEGATION_METADATA_KEY = "programmer_delegation"


@dataclass(frozen=True)
class ProgrammerDelegationResult:
    final_run: AgentRunTable


def build_technical_task_draft(*, message: str, assistant_excerpt: str) -> dict[str, Any]:
    """In-memory technical task draft (no persistence in AI.16)."""
    summary = (message or "").strip()[:500]
    excerpt = (assistant_excerpt or "").strip()[:2000]
    return {
        "kind": ProgrammerOutputKind.TECHNICAL_TASK_DRAFT.value,
        "title": TECHNICAL_TASK_DRAFT_TITLE,
        "summary": summary,
        "scope": (
            "Consultation-only skeleton: outline architecture, APIs, automation steps, "
            "and acceptance criteria. No repository, shell, deploy, or live integrations."
        ),
        "deliverables": [
            "Problem statement",
            "Proposed architecture",
            "API / integration outline",
            "Risks and out-of-scope items",
        ],
        "assistant_excerpt": excerpt,
        "persisted": False,
    }


def merge_programmer_output_payload(
    *,
    run: AgentRunTable,
    message: str,
) -> dict[str, Any]:
    output = dict(run.output_payload or {})
    llm_content = ""
    if isinstance(output.get("content"), str):
        llm_content = output["content"]
    elif isinstance(output.get("llm_content"), str):
        llm_content = output["llm_content"]
    output["programmer_mode"] = ProgrammerOutputKind.CONSULTATION.value
    output["technical_task_draft"] = build_technical_task_draft(
        message=message,
        assistant_excerpt=llm_content,
    )
    return output


async def resolve_project_programmer_agent_id(
    session: AsyncSession,
    owner_id: UUID,
    project_id: UUID,
) -> UUID:
    agents = await AgentService(session).list_agents(owner_id, project_id=project_id)
    matching = [
        agent
        for agent in agents
        if agent.type == AgentType.PROGRAMMER and agent.status != AgentStatus.ARCHIVED
    ]
    active = [agent for agent in matching if agent.status == AgentStatus.ACTIVE]
    pool = active or matching
    if not pool:
        raise NotFoundError("No programmer agent available in project")
    return pool[0].id


async def execute_programmer_delegation(
    session: AsyncSession,
    *,
    programmer_parent_run: AgentRunTable,
    input_payload: dict[str, Any],
    owner_id: UUID,
    message: str,
) -> ProgrammerDelegationResult:
    """
    Run a single Programmer child under General. No child runs, tools, or external execution.
    """
    agent_runs = AgentRunService(session)
    parent_agent = await agent_runs.get_executable_agent(programmer_parent_run.agent_id, owner_id)
    if parent_agent.type != AgentType.PROGRAMMER:
        raise ExecutorError("Programmer delegation requires programmer agent")

    final_run, _engine = await AgentRunCoordinator(session).execute_run(
        programmer_parent_run.id,
        owner_id,
        request_engine="classic",
    )
    if final_run.status != AgentRunStatus.SUCCEEDED:
        raise ExecutorError("Programmer specialist temporarily unavailable")

    enriched = merge_programmer_output_payload(run=final_run, message=message)
    persisted = await agent_runs.patch_output_payload(
        owner_id,
        final_run.id,
        enriched,
    )
    if persisted is None:
        raise ExecutorError("Programmer run output could not be saved")

    return ProgrammerDelegationResult(final_run=persisted)
