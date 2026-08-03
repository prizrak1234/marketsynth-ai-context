"""Direct specialist chat execution (Phase AI.18) — no General routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.direct_specialist.contracts import (
    DIRECT_SPECIALIST_DOMAIN_BY_AGENT,
    ENTRYPOINT_DIRECT_SPECIALIST,
)
from app.agents.direct_specialist.prompts import (
    MEDIA_DIRECT_CLARIFICATION,
    PROGRAMMER_DIRECT_CLARIFICATION,
)
from app.agents.general.contracts import GeneralDomain
from app.agents.general.router import detect_general_domain
from app.agents.marketer.orchestrator_delegation import (
    MarketerOrchestratorDelegationResult,
    execute_marketer_orchestrator_delegation,
)
from app.agents.media.execution import execute_media_delegation
from app.agents.programmer.execution import execute_programmer_delegation
from app.db.models.agent_run import AgentRunTable
from app.schemas.agent_chat import AgentChatSubagentChainEntry, AgentChatSubagentExecution
from app.schemas.contracts import AgentType

_DIRECT_DOMAIN_GATE: dict[AgentType, GeneralDomain] = {
    AgentType.PROGRAMMER: GeneralDomain.PROGRAMMER,
    AgentType.MEDIA: GeneralDomain.MEDIA,
}


def build_direct_specialist_run_metadata(*, domain: str) -> dict[str, Any]:
    base: dict[str, Any] = {"agent_chat": True}
    base["execution_metadata"] = {
        "entrypoint": ENTRYPOINT_DIRECT_SPECIALIST,
        "domain": domain,
    }
    return base


def message_fits_direct_specialist(*, agent_type: AgentType, message: str) -> bool:
    """Reuse General phrase taxonomy only as a scope gate — never invoke General execution."""
    expected = _DIRECT_DOMAIN_GATE.get(agent_type)
    if expected is None:
        return True
    return detect_general_domain(message=message) == expected


def direct_specialist_clarification(*, agent_type: AgentType) -> str:
    if agent_type == AgentType.PROGRAMMER:
        return PROGRAMMER_DIRECT_CLARIFICATION
    if agent_type == AgentType.MEDIA:
        return MEDIA_DIRECT_CLARIFICATION
    raise ValueError(f"No direct clarification for {agent_type.value}")


@dataclass(frozen=True)
class DirectSpecialistChatResult:
    domain: str
    clarification: str | None
    final_run: AgentRunTable | None
    subagent_chain: list[AgentChatSubagentChainEntry] | None
    subagent_execution: AgentChatSubagentExecution | None


async def execute_direct_specialist_chat(
    session: AsyncSession,
    *,
    parent_run: AgentRunTable,
    input_payload: dict[str, Any],
    owner_id: UUID,
    message: str,
    agent_type: AgentType,
) -> DirectSpecialistChatResult:
    domain = DIRECT_SPECIALIST_DOMAIN_BY_AGENT.get(agent_type)
    if domain is None:
        raise ValueError(f"Unsupported direct specialist agent type: {agent_type.value}")

    if not message_fits_direct_specialist(agent_type=agent_type, message=message):
        return DirectSpecialistChatResult(
            domain=domain,
            clarification=direct_specialist_clarification(agent_type=agent_type),
            final_run=None,
            subagent_chain=None,
            subagent_execution=None,
        )

    if agent_type == AgentType.ORCHESTRATOR:
        marketer_result: MarketerOrchestratorDelegationResult = (
            await execute_marketer_orchestrator_delegation(
                session,
                orchestrator_parent_run=parent_run,
                input_payload=input_payload,
                owner_id=owner_id,
            )
        )
        return DirectSpecialistChatResult(
            domain=domain,
            clarification=None,
            final_run=marketer_result.final_run,
            subagent_chain=marketer_result.subagent_chain,
            subagent_execution=marketer_result.subagent_execution,
        )

    if agent_type == AgentType.PROGRAMMER:
        programmer_result = await execute_programmer_delegation(
            session,
            programmer_parent_run=parent_run,
            input_payload=input_payload,
            owner_id=owner_id,
            message=message,
        )
        return DirectSpecialistChatResult(
            domain=domain,
            clarification=None,
            final_run=programmer_result.final_run,
            subagent_chain=None,
            subagent_execution=None,
        )

    if agent_type == AgentType.MEDIA:
        media_result = await execute_media_delegation(
            session,
            media_parent_run=parent_run,
            input_payload=input_payload,
            owner_id=owner_id,
            message=message,
        )
        return DirectSpecialistChatResult(
            domain=domain,
            clarification=None,
            final_run=media_result.final_run,
            subagent_chain=None,
            subagent_execution=None,
        )

    raise ValueError(f"Unsupported direct specialist agent type: {agent_type.value}")
