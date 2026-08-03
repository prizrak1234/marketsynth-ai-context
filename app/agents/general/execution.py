"""General agent execution — domain routing and specialist delegation (Phase AI.15–AI.17)."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.direct_specialist.contracts import ENTRYPOINT_GENERAL_DELEGATION
from app.agents.general.contracts import GeneralDomain
from app.agents.general.prompts import UNKNOWN_DOMAIN_CLARIFICATION
from app.agents.general.router import detect_general_domain
from app.agents.marketer.orchestrator_delegation import (
    execute_marketer_orchestrator_delegation,
    resolve_project_orchestrator_agent_id,
)
from app.agents.media.execution import execute_media_delegation, resolve_project_media_agent_id
from app.agents.programmer.execution import (
    execute_programmer_delegation,
    resolve_project_programmer_agent_id,
)
from app.agents.run_depth import compute_agent_run_depth, ensure_child_depth_allowed
from app.core.exceptions import InvalidStateError
from app.db.models.agent_run import AgentRunTable
from app.schemas.agent_chat import AgentChatSubagentChainEntry, AgentChatSubagentExecution
from app.schemas.contracts import AgentType
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService

GENERAL_DELEGATION_SOURCE = "general_delegation"
GENERAL_DELEGATION_METADATA_KEY = "general_delegation"
_MAX_DELEGATED_CHILDREN_PER_GENERAL = 1


@dataclass(frozen=True)
class GeneralExecutionResult:
    domain: GeneralDomain
    clarification: str | None
    delegated_child_run: AgentRunTable | None
    final_run: AgentRunTable | None
    subagent_chain: list[AgentChatSubagentChainEntry] | None
    subagent_execution: AgentChatSubagentExecution | None


def build_general_delegation_child_input(
    *,
    parent_run: AgentRunTable,
    input_payload: dict[str, Any],
    domain: GeneralDomain,
) -> dict[str, Any]:
    child_payload = copy.deepcopy(input_payload)
    child_payload["parent_agent_run_id"] = str(parent_run.id)
    child_payload["source"] = GENERAL_DELEGATION_SOURCE
    child_payload["delegated_domain"] = domain.value
    return child_payload


def build_general_delegation_child_metadata(
    *,
    parent_run: AgentRunTable,
    domain: GeneralDomain,
    specialist_agent_id: UUID,
) -> dict[str, Any]:
    metadata = dict(parent_run.run_metadata or {})
    metadata[GENERAL_DELEGATION_METADATA_KEY] = {
        "domain": domain.value,
        "parent_agent_run_id": str(parent_run.id),
        "specialist_agent_id": str(specialist_agent_id),
        "source": GENERAL_DELEGATION_SOURCE,
    }
    metadata["execution_metadata"] = {
        "entrypoint": ENTRYPOINT_GENERAL_DELEGATION,
        "domain": domain.value,
    }
    return metadata


async def _create_and_run_specialist(
    session: AsyncSession,
    *,
    parent_run: AgentRunTable,
    owner_id: UUID,
    child_input: dict[str, Any],
    domain: GeneralDomain,
    specialist_agent_id: UUID,
    message: str,
) -> GeneralExecutionResult:
    child_metadata = build_general_delegation_child_metadata(
        parent_run=parent_run,
        domain=domain,
        specialist_agent_id=specialist_agent_id,
    )
    delegated_child_run = await AgentRunService(session).create_run(
        owner_id,
        agent_id=specialist_agent_id,
        task_id=parent_run.task_id,
        input_payload=child_input,
        metadata=child_metadata,
        parent_agent_run_id=parent_run.id,
    )
    if delegated_child_run is None:
        raise InvalidStateError(f"{domain.value} specialist agent not found")
    return delegated_child_run


async def execute_general_agent(
    session: AsyncSession,
    *,
    parent_run: AgentRunTable,
    input_payload: dict[str, Any],
    owner_id: UUID,
    message: str,
) -> GeneralExecutionResult:
    """
    General parent run delegates to domain specialists; does not execute domain work itself.
    """
    general_depth = await compute_agent_run_depth(session, parent_run, owner_id)
    if general_depth != 0:
        raise InvalidStateError("General agent run must be top-level")

    general_agent = await AgentService(session).get_agent(parent_run.agent_id, owner_id)
    if general_agent is None or general_agent.type != AgentType.GENERAL:
        raise InvalidStateError("execute_general_agent requires General agent parent run")

    domain = detect_general_domain(message=message)
    if domain == GeneralDomain.UNKNOWN:
        return GeneralExecutionResult(
            domain=domain,
            clarification=UNKNOWN_DOMAIN_CLARIFICATION,
            delegated_child_run=None,
            final_run=None,
            subagent_chain=None,
            subagent_execution=None,
        )

    agent_runs = AgentRunService(session)
    existing = await agent_runs.count_children(parent_run.id, owner_id)
    if existing >= _MAX_DELEGATED_CHILDREN_PER_GENERAL:
        raise InvalidStateError("General run already delegated to a specialist")

    await ensure_child_depth_allowed(session, parent_run, owner_id)

    child_input = build_general_delegation_child_input(
        parent_run=parent_run,
        input_payload=input_payload,
        domain=domain,
    )

    if domain == GeneralDomain.MARKETING:
        specialist_agent_id = await resolve_project_orchestrator_agent_id(
            session,
            owner_id,
            parent_run.project_id,
        )
        delegated_child_run = await _create_and_run_specialist(
            session,
            parent_run=parent_run,
            owner_id=owner_id,
            child_input=child_input,
            domain=domain,
            specialist_agent_id=specialist_agent_id,
            message=message,
        )
        specialist_result = await execute_marketer_orchestrator_delegation(
            session,
            orchestrator_parent_run=delegated_child_run,
            input_payload=child_input,
            owner_id=owner_id,
        )
        return GeneralExecutionResult(
            domain=domain,
            clarification=None,
            delegated_child_run=delegated_child_run,
            final_run=specialist_result.final_run,
            subagent_chain=specialist_result.subagent_chain,
            subagent_execution=specialist_result.subagent_execution,
        )

    if domain == GeneralDomain.PROGRAMMER:
        specialist_agent_id = await resolve_project_programmer_agent_id(
            session,
            owner_id,
            parent_run.project_id,
        )
        delegated_child_run = await _create_and_run_specialist(
            session,
            parent_run=parent_run,
            owner_id=owner_id,
            child_input=child_input,
            domain=domain,
            specialist_agent_id=specialist_agent_id,
            message=message,
        )
        programmer_result = await execute_programmer_delegation(
            session,
            programmer_parent_run=delegated_child_run,
            input_payload=child_input,
            owner_id=owner_id,
            message=message,
        )
        return GeneralExecutionResult(
            domain=domain,
            clarification=None,
            delegated_child_run=delegated_child_run,
            final_run=programmer_result.final_run,
            subagent_chain=None,
            subagent_execution=None,
        )

    if domain == GeneralDomain.MEDIA:
        specialist_agent_id = await resolve_project_media_agent_id(
            session,
            owner_id,
            parent_run.project_id,
        )
        delegated_child_run = await _create_and_run_specialist(
            session,
            parent_run=parent_run,
            owner_id=owner_id,
            child_input=child_input,
            domain=domain,
            specialist_agent_id=specialist_agent_id,
            message=message,
        )
        media_result = await execute_media_delegation(
            session,
            media_parent_run=delegated_child_run,
            input_payload=child_input,
            owner_id=owner_id,
            message=message,
        )
        return GeneralExecutionResult(
            domain=domain,
            clarification=None,
            delegated_child_run=delegated_child_run,
            final_run=media_result.final_run,
            subagent_chain=None,
            subagent_execution=None,
        )

    raise InvalidStateError(f"Unsupported general domain: {domain.value}")
