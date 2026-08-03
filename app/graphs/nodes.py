"""LangGraph nodes — thin wrappers over existing prompt, LLM, and tool layers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig

from app.core.exceptions import ExecutorError
from app.db.base import utc_now
from app.graphs.context import GraphRunContext
from app.graphs.contracts import GRAPH_CONTEXT_CONFIG_KEY, AgentGraphStateDict
from app.graphs.handoff import (
    HANDOFF_STATUS_DELEGATED,
    HANDOFF_STATUS_REJECTED,
    GraphHandoffDecision,
    build_handoff_output_payload,
    count_parent_handoff_children,
    enqueue_handoff_child_run,
    evaluate_graph_handoff,
    extract_handoff_controls,
    handoff_depth_from_metadata,
    parse_orchestration_config,
    resolve_orchestrator_handoff_request,
)
from app.graphs.memory_node import load_graph_memory_context
from app.graphs.node_runner import run_graph_node
from app.graphs.tool_node import (
    build_tool_follow_up_messages,
    execute_graph_tool_round,
    finalize_initial_llm_after_tool_round,
    plan_graph_tool_round,
    serialize_tool_calls,
)
from app.llm.config import validate_llm_request_payload
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.observability import metrics_from_output
from app.llm.run_metadata import build_llm_run_metadata
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.schemas.contracts import AgentRunStatus, AgentType
from app.tools.executor import (
    build_tool_call_metadata,
    build_tools_run_summary,
    enrich_tool_round_metadata,
)


def _get_context(config: RunnableConfig) -> GraphRunContext:
    configurable = config.get("configurable") or {}
    ctx = configurable.get(GRAPH_CONTEXT_CONFIG_KEY)
    if ctx is None:
        raise ExecutorError("Graph run context is missing")
    return ctx


def _cost_estimate(output: Any) -> float | None:
    if output.estimated_cost_usd is None:
        return None
    return float(output.estimated_cost_usd)


def _extract_prompt_payload(
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], Any, Any, Any, Any, Any]:
    payload = dict(input_payload)
    memory_context = payload.pop("memory_context", None)
    user_context = payload.pop("user_context", None)
    mock_tool_call = payload.pop("mock_tool_call", None)
    debug_tool_call = payload.pop("debug_tool_call", None)
    force_tool_call = payload.pop("force_tool_call", None)
    return payload, memory_context, user_context, mock_tool_call, debug_tool_call, force_tool_call


def _serialize_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    return [message.model_dump(mode="json") for message in messages]


def _serialize_tool_results(results: list) -> list[dict[str, Any]]:
    return [result.model_dump(mode="json") for result in results]


def _memory_run_summary(state: AgentGraphStateDict) -> dict[str, Any]:
    return {
        "memory_load_status": state.get("memory_load_status"),
        "memory_item_count": int(state.get("memory_item_count") or 0),
    }


async def memory_load_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("memory_load", state, _memory_load_impl, config)


async def _memory_load_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    owner_id = UUID(str(state["owner_id"]))
    payload = dict(state["input_payload"])

    provided_memory = payload.pop("memory_context", None)
    skip_load = bool(payload.pop("skip_graph_memory_load", False))

    load_result = await load_graph_memory_context(
        ctx.session,
        owner_id=owner_id,
        project_id=ctx.run.project_id,
        agent_id=ctx.agent.id,
        input_payload=payload,
        provided_memory_context=provided_memory,
        skip_graph_memory_load=skip_load,
    )
    ctx.memory_context = load_result.memory_context

    return {
        "memory_load_status": load_result.status,
        "memory_item_count": load_result.item_count,
        "memory_query": load_result.memory_query,
        "memory_context": load_result.memory_context,
        "status": AgentRunStatus.RUNNING.value,
    }


async def handoff_gate_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("handoff_gate", state, _handoff_gate_impl, config)


async def _handoff_gate_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    owner_id = UUID(str(state["owner_id"]))
    cleaned_payload, handoff_request, target_type_hint = extract_handoff_controls(
        dict(state["input_payload"]),
    )

    if ctx.agent.type == AgentType.ORCHESTRATOR:
        orchestrator_request = await resolve_orchestrator_handoff_request(
            ctx.session,
            owner_id=owner_id,
            project_id=ctx.run.project_id,
            agent_config=dict(ctx.agent.config or {}),
            cleaned_payload=cleaned_payload,
            explicit_request=handoff_request,
            target_type_hint=target_type_hint,
        )
        if orchestrator_request is not None:
            handoff_request = orchestrator_request

    parent_depth = handoff_depth_from_metadata(dict(ctx.run.run_metadata or {}))
    if (
        ctx.agent.type == AgentType.ORCHESTRATOR
        and handoff_request is not None
    ):
        orchestration = parse_orchestration_config(dict(ctx.agent.config or {}))
        existing_children = await count_parent_handoff_children(
            ctx.session,
            owner_id=owner_id,
            parent_run_id=UUID(str(state["agent_run_id"])),
        )
        if existing_children >= orchestration.max_child_runs:
            ctx.handoff_decision = GraphHandoffDecision(
                status=HANDOFF_STATUS_REJECTED,
                target_agent_id=None,
                target_agent_type=None,
                target_agent_name=None,
                reason=handoff_request.reason,
                error="handoff_max_children_exceeded",
                options=handoff_request.options,
            )
            return {
                "input_payload": cleaned_payload,
                "handoff_status": HANDOFF_STATUS_REJECTED,
                "handoff_target_agent_id": None,
                "handoff_target_agent_type": None,
                "handoff_reason": handoff_request.reason,
                "status": AgentRunStatus.FAILED.value,
                "error": "handoff_max_children_exceeded",
            }

    decision = await evaluate_graph_handoff(
        ctx.session,
        owner_id=owner_id,
        project_id=ctx.run.project_id,
        source_agent_id=ctx.agent.id,
        source_agent_type=ctx.agent.type,
        request=handoff_request,
        parent_handoff_depth=parent_depth,
    )
    ctx.handoff_decision = decision

    update: AgentGraphStateDict = {
        "input_payload": cleaned_payload,
        "handoff_status": decision.status,
        "handoff_target_agent_id": (
            str(decision.target_agent_id) if decision.target_agent_id else None
        ),
        "handoff_target_agent_type": decision.target_agent_type,
        "handoff_reason": decision.reason,
        "status": AgentRunStatus.RUNNING.value,
    }

    if decision.status == HANDOFF_STATUS_REJECTED and decision.error:
        update["status"] = AgentRunStatus.FAILED.value
        update["error"] = decision.error

    return update


async def handoff_record_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("handoff_record", state, _handoff_record_impl, config)


async def _handoff_record_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    owner_id = UUID(str(state["owner_id"]))
    run_id = UUID(str(state["agent_run_id"]))
    finished_at = utc_now().isoformat()

    decision = ctx.handoff_decision
    if decision is None or decision.status != HANDOFF_STATUS_DELEGATED:
        raise ExecutorError("Handoff record invoked without a delegated handoff")

    cleaned_payload = dict(state.get("input_payload") or ctx.clean_input_payload or {})
    memory_context = (
        state.get("memory_context") if "memory_context" in state else ctx.memory_context
    )

    max_child_runs: int | None = None
    if ctx.agent.type == AgentType.ORCHESTRATOR:
        max_child_runs = parse_orchestration_config(
            dict(ctx.agent.config or {}),
        ).max_child_runs

    child_result = await enqueue_handoff_child_run(
        ctx.session,
        owner_id=owner_id,
        parent_run_id=run_id,
        task_id=ctx.run.task_id,
        target_agent_id=decision.target_agent_id,
        parent_payload=cleaned_payload,
        decision=decision,
        source_agent_id=ctx.agent.id,
        source_agent_type=ctx.agent.type.value,
        trace_id=ctx.trace_id,
        parent_handoff_depth=handoff_depth_from_metadata(dict(ctx.run.run_metadata or {})),
        memory_context=memory_context,
        max_child_runs=max_child_runs,
    )

    output_payload = build_handoff_output_payload(
        source_agent_id=ctx.agent.id,
        source_agent_type=ctx.agent.type.value,
        decision=decision,
        trace_id=ctx.trace_id,
        graph_version=ctx.graph_version,
        child=child_result,
    )
    await ctx.agent_runs.mark_succeeded(owner_id, run_id, output_payload)

    return {
        "output_payload": output_payload,
        "status": AgentRunStatus.SUCCEEDED.value,
        "error": None,
        "finished_at": finished_at,
        "handoff_status": HANDOFF_STATUS_DELEGATED,
        "child_agent_run_id": (
            str(child_result.child_run_id) if child_result.child_run_id else None
        ),
        "child_run_enqueued": child_result.child_run_enqueued,
        "child_run_executed": child_result.child_run_executed,
    }


async def build_prompt_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("build_prompt", state, _build_prompt_impl, config)


async def _build_prompt_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    (
        clean_payload,
        payload_memory,
        user_context,
        mock_tool_call,
        debug_tool_call,
        force_tool_call,
    ) = _extract_prompt_payload(dict(state["input_payload"]))
    ctx.clean_input_payload = clean_payload
    memory_context = ctx.memory_context if ctx.memory_context is not None else payload_memory
    ctx.memory_context = memory_context
    ctx.user_context = user_context

    prompt_build = build_llm_messages(
        PromptBuildInput(
            agent_id=ctx.agent.id,
            agent_type=ctx.agent.type,
            agent_config=ctx.agent.config,
            input_payload=clean_payload,
            memory_context=memory_context,
            user_context=user_context,
        ),
    )
    ctx.messages = prompt_build.messages
    ctx.prompt_build_metadata = prompt_build.metadata
    ctx.llm_metadata = build_llm_run_metadata(
        ctx.run_id,
        agent_type=ctx.agent.type,
        agent_config=ctx.agent.config if isinstance(ctx.agent.config, dict) else None,
        input_payload=clean_payload,
        mock_tool_call=mock_tool_call,
        debug_tool_call=debug_tool_call,
        force_tool_call=force_tool_call,
    )
    ctx.llm_metadata["executor"] = "langgraph-dry-run"

    ctx.tools_metadata = build_tool_call_metadata(
        available_tool_names=[tool.name for tool in ctx.available_tools],
        tool_results=[],
        tool_choice=ctx.tool_choice,
        permission_policy=ctx.permission_policy,
    )

    return {
        "messages": _serialize_messages(ctx.messages),
        "status": AgentRunStatus.RUNNING.value,
    }


async def llm_call_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("llm_call", state, _llm_call_impl, config)


async def _llm_call_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    owner_id = UUID(str(state["owner_id"]))

    prompt_metadata = {
        "executor": "langgraph-dry-run",
        "temperature": ctx.temperature,
        **ctx.prompt_build_metadata,
    }
    request_metadata = {
        "executor": "langgraph-dry-run",
        "max_tokens": ctx.max_tokens,
        "provider": ctx.provider.value,
        "model": ctx.model,
        "tools_metadata": ctx.tools_metadata,
        **ctx.prompt_build_metadata,
    }
    validate_llm_request_payload(
        input_payload=ctx.stored_input_payload,
        prompt_metadata=prompt_metadata,
        request_metadata=request_metadata,
    )

    llm_request = await ctx.llm_requests.create_request(
        owner_id,
        agent_run_id=ctx.run_id,
        provider=ctx.provider,
        model=ctx.model,
        input_payload=ctx.stored_input_payload,
        prompt_metadata=prompt_metadata,
        request_metadata=request_metadata,
    )
    if llm_request is None:
        raise ExecutorError("Failed to create LLM request")

    ctx.initial_llm_request_id = llm_request.id
    running = await ctx.llm_requests.mark_running(owner_id, llm_request.id)
    if running is None:
        raise ExecutorError("Failed to mark LLM request running")

    llm_output = await ctx.adapter.generate(
        LLMGenerateInput(
            provider=ctx.provider,
            model=ctx.model,
            messages=ctx.messages,
            temperature=ctx.temperature,
            max_tokens=ctx.max_tokens,
            tools=ctx.provider_tools,
            tool_choice=ctx.tool_choice,
            metadata=ctx.llm_metadata,
        ),
    )
    ctx.initial_llm_output = llm_output
    ctx.initial_tool_calls = list(llm_output.tool_calls or [])
    has_tool_calls = bool(ctx.initial_tool_calls)

    return {
        "has_tool_calls": has_tool_calls,
        "follow_up_llm_call": False,
        "status": AgentRunStatus.RUNNING.value,
    }


async def tool_prepare_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("tool_prepare", state, _tool_prepare_impl, config)


async def _tool_prepare_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    if not ctx.initial_tool_calls:
        return {
            "tool_calls_planned": 0,
            "tool_calls_skipped": 0,
            "pending_tool_calls": [],
            "tool_round_status": "empty",
            "follow_up_llm_call": False,
        }

    plan = plan_graph_tool_round(ctx.initial_tool_calls)
    ctx.tool_round_plan = plan

    return {
        "pending_tool_calls": serialize_tool_calls(plan.accepted_calls),
        "tool_calls_planned": len(plan.accepted_calls),
        "tool_calls_skipped": len(plan.skipped_calls),
        "tool_round_status": "planned",
        "follow_up_llm_call": True,
        "status": AgentRunStatus.RUNNING.value,
    }


async def tool_execute_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("tool_execute", state, _tool_execute_impl, config)


async def _tool_execute_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    owner_id = UUID(str(state["owner_id"]))
    llm_request_id = ctx.initial_llm_request_id
    if llm_request_id is None:
        raise ExecutorError("Initial LLM request id is missing")

    plan = ctx.tool_round_plan
    if plan is None:
        plan = plan_graph_tool_round(ctx.initial_tool_calls)

    round_result = await execute_graph_tool_round(
        session=ctx.session,
        ctx=ctx,
        owner_id=owner_id,
        llm_request_id=llm_request_id,
        plan=plan,
        available_tools=ctx.available_tools,
        tool_choice=ctx.tool_choice,
        permission_policy=ctx.permission_policy,
    )

    ctx.tool_round_result = round_result
    ctx.tool_results = round_result.tool_results
    ctx.budgeted_tool_results = round_result.budgeted_tool_results
    ctx.tools_metadata = round_result.tools_metadata

    return {
        "tool_results": _serialize_tool_results(ctx.tool_results),
        "tool_calls_executed": round_result.accepted_count,
        "tool_round_status": "executed",
        "status": AgentRunStatus.RUNNING.value,
    }


async def tool_finalize_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("tool_finalize", state, _tool_finalize_impl, config)


async def _tool_finalize_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    owner_id = UUID(str(state["owner_id"]))
    llm_request_id = ctx.initial_llm_request_id
    if llm_request_id is None:
        raise ExecutorError("Initial LLM request id is missing")
    round_result = ctx.tool_round_result
    if round_result is None:
        raise ExecutorError("Tool round result is missing before finalize")

    await finalize_initial_llm_after_tool_round(
        ctx=ctx,
        owner_id=owner_id,
        llm_request_id=llm_request_id,
        round_result=round_result,
    )

    return {
        "follow_up_llm_call": True,
        "tool_round_status": "complete",
        "status": AgentRunStatus.RUNNING.value,
    }


async def llm_follow_up_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("llm_follow_up", state, _llm_follow_up_impl, config)


async def _llm_follow_up_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    owner_id = UUID(str(state["owner_id"]))
    llm_request_id = ctx.initial_llm_request_id
    if llm_request_id is None:
        raise ExecutorError("Initial LLM request id is missing")

    follow_up_messages = build_tool_follow_up_messages(
        base_messages=list(ctx.messages),
        tool_calls=ctx.initial_tool_calls,
        initial_output=ctx.initial_llm_output,
        budgeted_results=ctx.budgeted_tool_results,
    )

    follow_up_request_metadata = {
        "executor": "langgraph-dry-run",
        "max_tokens": ctx.max_tokens,
        "provider": ctx.provider.value,
        "model": ctx.model,
        "phase": "tool_follow_up",
        "parent_request_id": str(llm_request_id),
        "tools_metadata": ctx.tools_metadata,
        **ctx.prompt_build_metadata,
    }
    validate_llm_request_payload(
        input_payload=ctx.stored_input_payload,
        prompt_metadata=ctx.prompt_metadata,
        request_metadata=follow_up_request_metadata,
    )

    follow_up_request = await ctx.llm_requests.create_request(
        owner_id,
        agent_run_id=ctx.run_id,
        provider=ctx.provider,
        model=ctx.model,
        input_payload=ctx.stored_input_payload,
        prompt_metadata=ctx.prompt_metadata,
        request_metadata=follow_up_request_metadata,
    )
    if follow_up_request is None:
        raise ExecutorError("Failed to create follow-up LLM request")

    ctx.follow_up_llm_request_id = follow_up_request.id
    running_follow_up = await ctx.llm_requests.mark_running(owner_id, follow_up_request.id)
    if running_follow_up is None:
        raise ExecutorError("Failed to mark follow-up LLM request running")

    follow_up_metadata = build_llm_run_metadata(
        ctx.run_id,
        agent_type=ctx.agent.type,
        agent_config=ctx.agent.config if isinstance(ctx.agent.config, dict) else None,
        input_payload=ctx.clean_input_payload,
    )
    follow_up_metadata["phase"] = "tool_follow_up"
    follow_up_metadata["executor"] = "langgraph-dry-run"

    follow_up_output = await ctx.adapter.generate(
        LLMGenerateInput(
            provider=ctx.provider,
            model=ctx.model,
            messages=follow_up_messages,
            temperature=ctx.temperature,
            max_tokens=ctx.max_tokens,
            tools=None,
            tool_choice=None,
            metadata=follow_up_metadata,
        ),
    )
    ctx.follow_up_llm_output = follow_up_output

    if follow_up_output.tool_calls:
        nested_metadata = enrich_tool_round_metadata(
            ctx.tools_metadata,
            tool_rounds=1,
            follow_up_llm_call=True,
            nested_tool_calls=True,
        )
        error = "nested_tool_calls_not_supported"
        await ctx.llm_requests.mark_failed(
            owner_id,
            follow_up_request.id,
            error,
            request_metadata={
                **follow_up_request_metadata,
                "tools_metadata": nested_metadata,
            },
        )
        return {
            "error": error,
            "status": AgentRunStatus.FAILED.value,
            "follow_up_llm_call": True,
        }

    follow_up_observability = metrics_from_output(follow_up_output).to_metadata()
    follow_up_succeeded = await ctx.llm_requests.mark_succeeded(
        owner_id,
        follow_up_request.id,
        output_payload={
            "content": follow_up_output.content,
            "provider": follow_up_output.provider.value,
            "model": follow_up_output.model or ctx.model,
            "finish_reason": follow_up_output.finish_reason,
        },
        raw_response={},
        input_tokens=int(follow_up_output.usage.get("input_tokens", 0)),
        output_tokens=int(follow_up_output.usage.get("output_tokens", 0)),
        total_tokens=int(follow_up_output.usage.get("total_tokens", 0)),
        cost_estimate=_cost_estimate(follow_up_output),
        latency_ms=follow_up_output.latency_ms or 0,
        response_metadata={
            "executor": "langgraph-dry-run",
            "phase": "tool_follow_up",
            "tools_metadata": ctx.tools_metadata,
            **follow_up_observability,
        },
        request_metadata_update={
            **ctx.prompt_build_metadata,
            **follow_up_observability,
            "tools_metadata": ctx.tools_metadata,
        },
    )
    if follow_up_succeeded is None or follow_up_succeeded.response is None:
        raise ExecutorError("Failed to complete follow-up LLM request")

    ctx.follow_up_llm_response_id = follow_up_succeeded.response.id

    return {
        "messages": _serialize_messages(follow_up_messages),
        "follow_up_llm_call": True,
        "status": AgentRunStatus.RUNNING.value,
    }


async def final_response_node(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    return await run_graph_node("final_response", state, _final_response_impl, config)


async def _final_response_impl(
    state: AgentGraphStateDict,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)
    owner_id = UUID(str(state["owner_id"]))
    run_id = UUID(str(state["agent_run_id"]))
    finished_at = utc_now().isoformat()

    error = state.get("error")
    if error:
        if state.get("handoff_status") == HANDOFF_STATUS_REJECTED:
            await ctx.agent_runs.mark_failed(owner_id, run_id, str(error))
            return {
                "output_payload": {},
                "status": AgentRunStatus.FAILED.value,
                "error": str(error),
                "finished_at": finished_at,
            }
        if ctx.follow_up_llm_request_id is not None and state.get("follow_up_llm_call"):
            pass
        elif ctx.initial_llm_request_id is not None:
            await ctx.llm_requests.mark_failed(
                owner_id,
                ctx.initial_llm_request_id,
                str(error),
            )
        await ctx.agent_runs.mark_failed(owner_id, run_id, str(error))
        return {
            "output_payload": {},
            "status": AgentRunStatus.FAILED.value,
            "error": str(error),
            "finished_at": finished_at,
        }

    if state.get("has_tool_calls"):
        follow_up = ctx.follow_up_llm_output
        if follow_up is None or ctx.follow_up_llm_request_id is None:
            raise ExecutorError("Follow-up LLM output is missing")
        audit_summary = (
            ctx.audit_tracker.to_summary()
            if ctx.audit_tracker is not None
            else {"logged_count": 0, "failed_to_log_count": 0}
        )
        output_payload: dict[str, Any] = {
            "content": follow_up.content,
            "llm_request_id": str(ctx.follow_up_llm_request_id),
            "llm_response_id": str(ctx.follow_up_llm_response_id or ""),
            "provider": follow_up.provider.value,
            "model": follow_up.model or ctx.model,
            "latency_ms": follow_up.latency_ms,
            "retry_count": follow_up.retry_count,
            "initial_llm_request_id": str(ctx.initial_llm_request_id),
            "tool_rounds": 1,
            "follow_up_llm_call": True,
            "tool_audit": audit_summary,
            "tools": build_tools_run_summary(ctx.tool_results),
            "execution_engine": "langgraph",
            "trace_id": ctx.trace_id,
            "graph_version": ctx.graph_version,
            "memory": _memory_run_summary(state),
        }
        await ctx.agent_runs.mark_succeeded(owner_id, run_id, output_payload)
        return {
            "output_payload": output_payload,
            "status": AgentRunStatus.SUCCEEDED.value,
            "error": None,
            "finished_at": finished_at,
        }

    initial = ctx.initial_llm_output
    llm_request_id = ctx.initial_llm_request_id
    if initial is None or llm_request_id is None:
        raise ExecutorError("Initial LLM output is missing")

    observability = metrics_from_output(initial).to_metadata()
    succeeded = await ctx.llm_requests.mark_succeeded(
        owner_id,
        llm_request_id,
        output_payload={
            "content": initial.content,
            "provider": initial.provider.value,
            "model": initial.model or ctx.model,
        },
        raw_response={},
        input_tokens=int(initial.usage.get("input_tokens", 0)),
        output_tokens=int(initial.usage.get("output_tokens", 0)),
        total_tokens=int(initial.usage.get("total_tokens", 0)),
        cost_estimate=_cost_estimate(initial),
        latency_ms=initial.latency_ms or 0,
        response_metadata={
            "executor": "langgraph-dry-run",
            "tools_metadata": ctx.tools_metadata,
            **observability,
        },
        request_metadata_update={
            **ctx.prompt_build_metadata,
            **observability,
            "tools_metadata": ctx.tools_metadata,
        },
    )
    if succeeded is None or succeeded.response is None:
        raise ExecutorError("Failed to complete LLM request")

    output_payload = {
        "content": initial.content,
        "llm_request_id": str(llm_request_id),
        "llm_response_id": str(succeeded.response.id),
        "provider": initial.provider.value,
        "model": initial.model or ctx.model,
        "latency_ms": initial.latency_ms,
        "retry_count": initial.retry_count,
        "execution_engine": "langgraph",
        "trace_id": ctx.trace_id,
        "graph_version": ctx.graph_version,
        "memory": _memory_run_summary(state),
    }
    await ctx.agent_runs.mark_succeeded(owner_id, run_id, output_payload)
    return {
        "output_payload": output_payload,
        "status": AgentRunStatus.SUCCEEDED.value,
        "error": None,
        "finished_at": finished_at,
        "trace_id": ctx.trace_id,
        "graph_version": ctx.graph_version,
    }
