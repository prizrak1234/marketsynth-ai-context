"""Graph node lifecycle — step limits, trace fields, safe errors, checkpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.core.exceptions import ExecutorError
from app.db.base import utc_now
from app.graphs.checkpoints import GraphCheckpoint
from app.graphs.context import GraphRunContext
from app.graphs.contracts import (
    GRAPH_CONTEXT_CONFIG_KEY,
    AgentGraphStateDict,
    assert_no_graph_state_secrets,
    state_snapshot_for_checkpoint,
)
from app.schemas.contracts import AgentRunStatus

NodeFn = Callable[[AgentGraphStateDict, RunnableConfig], Awaitable[AgentGraphStateDict]]

FORBIDDEN_STATE_UPDATE_KEYS = frozenset(
    {
        "raw_response",
        "session",
        "adapter",
        "checkpoint_store",
    },
)


def _get_context(config: RunnableConfig) -> GraphRunContext:
    configurable = config.get("configurable") or {}
    ctx = configurable.get(GRAPH_CONTEXT_CONFIG_KEY)
    if ctx is None:
        raise ExecutorError("Graph run context is missing")
    return ctx


def _safe_error_record(
    node_name: str,
    exc: BaseException,
) -> dict[str, Any]:
    message = str(exc).strip() or type(exc).__name__
    lowered = message.lower()
    if "sk-" in lowered or "api_key" in lowered or "authorization" in lowered:
        message = "Graph node execution failed"
    return {
        "node": node_name,
        "error_type": type(exc).__name__,
        "safe_message": message,
    }


def _merge_state(
    state: AgentGraphStateDict,
    update: AgentGraphStateDict,
) -> AgentGraphStateDict:
    for key in FORBIDDEN_STATE_UPDATE_KEYS:
        if key in update:
            raise ValueError(f"Graph state update must not include forbidden key: {key}")
    merged: AgentGraphStateDict = dict(state)
    merged.update(update)
    return merged


def _is_failure_state(state: AgentGraphStateDict) -> bool:
    if state.get("error"):
        return True
    status = state.get("status")
    return status == AgentRunStatus.FAILED.value or status == AgentRunStatus.FAILED


async def _save_checkpoint(
    ctx: GraphRunContext,
    *,
    node_name: str,
    state: AgentGraphStateDict,
) -> None:
    if not ctx.checkpoints_enabled:
        return
    snapshot = state_snapshot_for_checkpoint(state)
    assert_no_graph_state_secrets(snapshot)
    await ctx.checkpoint_store.save(
        GraphCheckpoint(
            trace_id=ctx.trace_id,
            agent_run_id=ctx.run_id,
            node_name=node_name,
            state_snapshot=snapshot,
        ),
    )


async def run_graph_node(
    node_name: str,
    state: AgentGraphStateDict,
    fn: NodeFn,
    config: RunnableConfig,
) -> AgentGraphStateDict:
    ctx = _get_context(config)

    if _is_failure_state(state) and node_name != "final_response":
        return dict(state)

    step_count = int(state.get("step_count", 0)) + 1
    max_steps = int(state.get("max_steps", ctx.max_steps))

    working: AgentGraphStateDict = {
        **state,
        "current_node": node_name,
        "step_count": step_count,
    }

    if step_count > max_steps:
        node_errors = list(working.get("node_errors") or [])
        node_errors.append(
            {
                "node": node_name,
                "error_type": "MaxStepsExceeded",
                "safe_message": "Graph step limit exceeded",
            },
        )
        failed: AgentGraphStateDict = {
            **working,
            "failed_node": node_name,
            "node_errors": node_errors,
            "status": AgentRunStatus.FAILED.value,
            "error": "graph_max_steps_exceeded",
            "finished_at": utc_now().isoformat(),
        }
        assert_no_graph_state_secrets(failed)
        return failed

    try:
        update = await fn(working, config)
        merged = _merge_state(working, update)

        if _is_failure_state(merged):
            node_errors = list(merged.get("node_errors") or [])
            if merged.get("error"):
                node_errors.append(
                    {
                        "node": node_name,
                        "error_type": "GraphNodeFailed",
                        "safe_message": str(merged["error"]),
                    },
                )
            merged["failed_node"] = node_name
            merged["node_errors"] = node_errors
            if not merged.get("finished_at"):
                merged["finished_at"] = utc_now().isoformat()
            assert_no_graph_state_secrets(merged)
            return merged

        completed = list(merged.get("completed_nodes") or [])
        if node_name not in completed:
            completed.append(node_name)
        merged["completed_nodes"] = completed
        merged["current_node"] = node_name

        await _save_checkpoint(ctx, node_name=node_name, state=merged)
        assert_no_graph_state_secrets(merged)
        return merged

    except Exception as exc:
        node_errors = list(working.get("node_errors") or [])
        node_errors.append(_safe_error_record(node_name, exc))
        failed = {
            **working,
            "failed_node": node_name,
            "node_errors": node_errors,
            "status": AgentRunStatus.FAILED.value,
            "error": _safe_error_record(node_name, exc)["safe_message"],
            "finished_at": utc_now().isoformat(),
        }
        assert_no_graph_state_secrets(failed)
        return failed
