"""Graph tool-round layer — plan, execute, and finalize read-only tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ExecutorError
from app.graphs.context import GraphRunContext
from app.llm.contracts import LLMGenerateOutput, LLMMessage
from app.llm.observability import metrics_from_output
from app.services.memory_service import MemoryService
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.context_budget import apply_tool_results_context_budget
from app.tools.contracts import ToolCall, ToolDefinition, ToolExecutionContext, ToolResult
from app.tools.executor import (
    SafeNoOpToolExecutor,
    build_tool_call_limit_exceeded_result,
    build_tool_call_metadata,
    enrich_tool_round_metadata,
)
from app.tools.registry import get_tool_registry
from app.tools.result_messages import build_assistant_tool_call_message, build_tool_result_message


@dataclass(frozen=True)
class GraphToolRoundPlan:
    accepted_calls: list[ToolCall]
    skipped_calls: list[ToolCall]
    max_per_round: int


@dataclass(frozen=True)
class GraphToolRoundResult:
    tool_results: list[ToolResult]
    budgeted_tool_results: list[ToolResult]
    tools_metadata: dict[str, Any]
    accepted_count: int
    skipped_count: int


def serialize_tool_calls(tool_calls: list[ToolCall]) -> list[dict[str, Any]]:
    return [call.model_dump(mode="json") for call in tool_calls]


def deserialize_tool_calls(payload: list[dict[str, Any]]) -> list[ToolCall]:
    return [ToolCall.model_validate(item) for item in payload]


def plan_graph_tool_round(
    tool_calls: list[ToolCall],
    *,
    max_per_round: int | None = None,
) -> GraphToolRoundPlan:
    limit = max_per_round if max_per_round is not None else get_settings().max_tool_calls_per_round
    accepted = list(tool_calls[:limit])
    skipped = list(tool_calls[limit:])
    return GraphToolRoundPlan(
        accepted_calls=accepted,
        skipped_calls=skipped,
        max_per_round=limit,
    )


def build_safe_noop_tool_executor(session: AsyncSession) -> SafeNoOpToolExecutor:
    return SafeNoOpToolExecutor(
        get_tool_registry(),
        memory_service=MemoryService(session),
        audit_service=ToolExecutionLogService(session),
        session=session,
    )


def build_tool_execution_context(
    ctx: GraphRunContext,
    *,
    owner_id: UUID,
    llm_request_id: UUID,
) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=ctx.run.project_id,
        agent_id=ctx.agent.id,
        agent_type=ctx.agent.type,
        agent_run_id=ctx.run_id,
        task_id=ctx.run.task_id,
        request_id=llm_request_id,
        audit_tracker=ctx.audit_tracker,
    )


async def execute_graph_tool_round(
    *,
    session: AsyncSession,
    ctx: GraphRunContext,
    owner_id: UUID,
    llm_request_id: UUID,
    plan: GraphToolRoundPlan,
    available_tools: list[ToolDefinition],
    tool_choice: str | None,
    permission_policy: dict[str, Any],
    executor: SafeNoOpToolExecutor | None = None,
) -> GraphToolRoundResult:
    """Execute accepted tool calls and synthesize limit-exceeded results for skipped calls."""
    tool_context = build_tool_execution_context(
        ctx,
        owner_id=owner_id,
        llm_request_id=llm_request_id,
    )
    runner = executor or build_safe_noop_tool_executor(session)

    tool_results: list[ToolResult] = []
    for tool_call in plan.accepted_calls:
        tool_results.append(await runner.execute(tool_call, tool_context))
    for tool_call in plan.skipped_calls:
        tool_results.append(build_tool_call_limit_exceeded_result(tool_call))

    budgeted = apply_tool_results_context_budget(tool_results)
    tools_metadata = enrich_tool_round_metadata(
        build_tool_call_metadata(
            available_tool_names=[tool.name for tool in available_tools],
            tool_results=tool_results,
            tool_choice=tool_choice,
            permission_policy=permission_policy,
        ),
        tool_rounds=1,
        follow_up_llm_call=True,
        nested_tool_calls=False,
    )

    return GraphToolRoundResult(
        tool_results=tool_results,
        budgeted_tool_results=budgeted,
        tools_metadata=tools_metadata,
        accepted_count=len(plan.accepted_calls),
        skipped_count=len(plan.skipped_calls),
    )


def _cost_estimate(output: LLMGenerateOutput) -> float | None:
    if output.estimated_cost_usd is None:
        return None
    return float(output.estimated_cost_usd)


async def finalize_initial_llm_after_tool_round(
    *,
    ctx: GraphRunContext,
    owner_id: UUID,
    llm_request_id: UUID,
    round_result: GraphToolRoundResult,
) -> None:
    """Mark the initial LLM request succeeded after tool results are attached."""
    initial_output = ctx.initial_llm_output
    if initial_output is None:
        raise ExecutorError("Initial LLM output is missing")

    first_observability = metrics_from_output(initial_output).to_metadata()
    first_succeeded = await ctx.llm_requests.mark_succeeded(
        owner_id,
        llm_request_id,
        output_payload={
            "content": initial_output.content,
            "provider": initial_output.provider.value,
            "model": initial_output.model or ctx.model,
            "finish_reason": initial_output.finish_reason,
            "tool_calls_detected": len(ctx.initial_tool_calls),
            "tool_calls_executed": round_result.accepted_count,
            "tool_calls_skipped": round_result.skipped_count,
        },
        raw_response={},
        input_tokens=int(initial_output.usage.get("input_tokens", 0)),
        output_tokens=int(initial_output.usage.get("output_tokens", 0)),
        total_tokens=int(initial_output.usage.get("total_tokens", 0)),
        cost_estimate=_cost_estimate(initial_output),
        latency_ms=initial_output.latency_ms or 0,
        response_metadata={
            "executor": "langgraph-dry-run",
            "phase": "initial",
            "tools_metadata": round_result.tools_metadata,
            **first_observability,
        },
        request_metadata_update={
            **ctx.prompt_build_metadata,
            **first_observability,
            "tools_metadata": round_result.tools_metadata,
        },
    )
    if first_succeeded is None or first_succeeded.response is None:
        raise ExecutorError("Failed to complete initial LLM request")


def build_tool_follow_up_messages(
    *,
    base_messages: list[LLMMessage],
    tool_calls: list[ToolCall],
    initial_output: LLMGenerateOutput | None,
    budgeted_results: list[ToolResult],
) -> list[LLMMessage]:
    follow_up_messages = list(base_messages)
    follow_up_messages.append(
        build_assistant_tool_call_message(
            tool_calls,
            content=(initial_output.content if initial_output else None),
        ),
    )
    for tool_call, tool_result in zip(tool_calls, budgeted_results, strict=True):
        follow_up_messages.append(build_tool_result_message(tool_call, tool_result))
    return follow_up_messages
