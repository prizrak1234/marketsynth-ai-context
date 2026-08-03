"""Sequential multi-subagent chain execution (Phase AI.14)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.marketer.chains import (
    MAX_SUBAGENT_CHAIN_LENGTH,
    MarketingExecutionChain,
    validate_chain,
)
from app.agents.marketer.compact_output import compact_subagent_output
from app.agents.marketer.contracts import MarketerSubAgentType
from app.agents.marketer.execution import (
    SUBAGENT_EXECUTION_METADATA_KEY,
    _SUPPORTED_SUBAGENTS,
    run_subagent_child,
)
from app.core.exceptions import ExecutorError, InvalidStateError
from app.db.models.agent_run import AgentRunTable
from app.services.agent_runs import AgentRunService


@dataclass(frozen=True)
class SubagentChainStepResult:
    subagent_type: MarketerSubAgentType
    agent_run: AgentRunTable


@dataclass(frozen=True)
class SubagentChainExecutionResult:
    steps: tuple[SubagentChainStepResult, ...]
    final_run: AgentRunTable


async def execute_subagent_chain(
    session: AsyncSession,
    *,
    parent_run: AgentRunTable,
    chain: MarketingExecutionChain,
    input_payload: dict[str, Any],
    owner_id: UUID,
) -> SubagentChainExecutionResult:
    """
    Run sub-agents sequentially; all children are siblings under parent_run (same parent_agent_run_id).
    """
    validated = validate_chain(chain)
    for subagent_type in validated:
        if subagent_type not in _SUPPORTED_SUBAGENTS:
            raise InvalidStateError(f"Sub-agent execution not supported for {subagent_type.value}")

    agent_runs = AgentRunService(session)
    existing_children = await agent_runs.count_children(parent_run.id, owner_id)
    if existing_children + len(validated) > MAX_SUBAGENT_CHAIN_LENGTH:
        raise InvalidStateError(
            f"Chain length {len(validated)} exceeds remaining capacity "
            f"({MAX_SUBAGENT_CHAIN_LENGTH - existing_children} slots)",
        )

    previous_output: dict[str, Any] | None = None
    steps: list[SubagentChainStepResult] = []

    for index, subagent_type in enumerate(validated):
        chain_metadata = {
            SUBAGENT_EXECUTION_METADATA_KEY: {
                "subagent": subagent_type.value,
                "parent_agent_run_id": str(parent_run.id),
                "chain_index": index,
                "chain_length": len(validated),
            },
        }
        final_run = await run_subagent_child(
            session,
            parent_run=parent_run,
            subagent_type=subagent_type,
            input_payload=input_payload,
            owner_id=owner_id,
            run_metadata=chain_metadata,
            previous_child_output=previous_output,
        )
        steps.append(SubagentChainStepResult(subagent_type=subagent_type, agent_run=final_run))
        previous_output = compact_subagent_output(dict(final_run.output_payload or {}))

    if not steps:
        raise ExecutorError("Sub-agent chain produced no runs")

    return SubagentChainExecutionResult(steps=tuple(steps), final_run=steps[-1].agent_run)
