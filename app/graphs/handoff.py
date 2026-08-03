"""Graph handoff policy — explicit delegation between agents (skeleton, no child execution)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.marketing.orchestration import (
    OrchestrationConfig,
    build_specialist_child_payload,
    parse_handoff_target_agent_type,
    parse_orchestration_config,
    resolve_project_agent_id_for_type,
    resolve_specialist_agent_type,
)
from app.schemas.contracts import AgentRunStatus, AgentStatus, AgentType
from app.services.agents import AgentService
from app.tools.security import sanitize_tool_payload

HANDOFF_STATUS_NONE = "none"
HANDOFF_STATUS_DELEGATED = "delegated"
HANDOFF_STATUS_REJECTED = "rejected"
HANDOFF_CHILD_EXECUTION_ENGINE = "langgraph-handoff-child"

ALLOWED_HANDOFF_TARGETS: dict[AgentType, frozenset[AgentType]] = {
    AgentType.ORCHESTRATOR: frozenset(
        {
            AgentType.STRATEGIST,
            AgentType.RESEARCHER,
            AgentType.COPYWRITER,
            AgentType.CONTENT_PLANNER,
            AgentType.CRITIC,
            AgentType.ANALYST,
        },
    ),
    AgentType.STRATEGIST: frozenset(
        {
            AgentType.RESEARCHER,
            AgentType.COPYWRITER,
            AgentType.CRITIC,
            AgentType.ANALYST,
        },
    ),
    AgentType.RESEARCHER: frozenset(
        {
            AgentType.STRATEGIST,
            AgentType.COPYWRITER,
            AgentType.ANALYST,
        },
    ),
    AgentType.COPYWRITER: frozenset({AgentType.CRITIC, AgentType.STRATEGIST}),
    AgentType.CONTENT_PLANNER: frozenset({AgentType.COPYWRITER, AgentType.CRITIC}),
    AgentType.CRITIC: frozenset({AgentType.COPYWRITER, AgentType.STRATEGIST}),
    AgentType.ANALYST: frozenset({AgentType.STRATEGIST, AgentType.RESEARCHER}),
}


@dataclass(frozen=True)
class GraphHandoffOptions:
    enqueue_child: bool = True
    execute_child: bool = False


@dataclass(frozen=True)
class GraphHandoffRequest:
    target_agent_id: UUID
    reason: str | None
    options: GraphHandoffOptions = GraphHandoffOptions()
    enqueue_explicit: bool = False
    execute_explicit: bool = False


@dataclass(frozen=True)
class GraphHandoffDecision:
    status: str
    target_agent_id: UUID | None
    target_agent_type: str | None
    target_agent_name: str | None
    reason: str | None
    error: str | None
    options: GraphHandoffOptions


@dataclass(frozen=True)
class GraphHandoffChildResult:
    child_run_id: UUID | None
    child_run_enqueued: bool
    child_run_executed: bool
    child_run_status: str | None
    child_run_error: str | None


def is_handoff_child_run(metadata: dict[str, Any] | None) -> bool:
    if not metadata:
        return False
    if metadata.get("execution_engine") != HANDOFF_CHILD_EXECUTION_ENGINE:
        return False
    parent_id = metadata.get("parent_agent_run_id")
    return isinstance(parent_id, str) and bool(parent_id.strip())


def handoff_depth_from_metadata(metadata: dict[str, Any] | None) -> int:
    if not metadata:
        return 0
    raw = metadata.get("handoff_depth", 0)
    if isinstance(raw, bool):
        return 0
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def extract_handoff_controls(
    input_payload: dict[str, Any],
) -> tuple[dict[str, Any], GraphHandoffRequest | None, AgentType | None]:
    """Remove handoff control keys from the run input payload."""
    payload = dict(input_payload)
    raw_target = payload.pop("handoff_to_agent_id", None)
    raw_reason = payload.pop("handoff_reason", None)
    raw_enqueue = payload.pop("handoff_enqueue_child", None)
    raw_execute = payload.pop("handoff_execute_child", None)
    raw_target_type = payload.pop("handoff_target_agent_type", None)
    target_type_hint = parse_handoff_target_agent_type(raw_target_type)

    reason: str | None = None
    if isinstance(raw_reason, str) and raw_reason.strip():
        sanitized = sanitize_tool_payload({"reason": raw_reason.strip()})
        value = sanitized.get("reason", "")
        reason = str(value)[:500] if value else None

    enqueue_explicit = raw_enqueue is not None
    execute_explicit = raw_execute is not None
    enqueue_child = True if raw_enqueue is None else bool(raw_enqueue)
    execute_child = bool(raw_execute) if raw_execute is not None else False
    options = GraphHandoffOptions(
        enqueue_child=enqueue_child,
        execute_child=execute_child,
    )

    if raw_target is None:
        return payload, None, target_type_hint

    if isinstance(raw_target, UUID):
        target_id = raw_target
    elif isinstance(raw_target, str) and raw_target.strip():
        try:
            target_id = UUID(raw_target.strip())
        except ValueError:
            return payload, None, target_type_hint
    else:
        return payload, None, target_type_hint

    return (
        payload,
        GraphHandoffRequest(
            target_agent_id=target_id,
            reason=reason,
            options=options,
            enqueue_explicit=enqueue_explicit,
            execute_explicit=execute_explicit,
        ),
        target_type_hint,
    )


def apply_orchestration_handoff_options(
    request: GraphHandoffRequest,
    orchestration: OrchestrationConfig,
) -> GraphHandoffRequest:
    enqueue_child = (
        request.options.enqueue_child
        if request.enqueue_explicit
        else True
    )
    execute_child = (
        request.options.execute_child
        if request.execute_explicit
        else orchestration.default_inline_child_execution
    )
    return GraphHandoffRequest(
        target_agent_id=request.target_agent_id,
        reason=request.reason,
        options=GraphHandoffOptions(
            enqueue_child=enqueue_child,
            execute_child=execute_child,
        ),
        enqueue_explicit=request.enqueue_explicit,
        execute_explicit=request.execute_explicit,
    )


async def resolve_orchestrator_handoff_request(
    session: AsyncSession,
    *,
    owner_id: UUID,
    project_id: UUID,
    agent_config: dict[str, Any] | None,
    cleaned_payload: dict[str, Any],
    explicit_request: GraphHandoffRequest | None,
    target_type_hint: AgentType | None,
) -> GraphHandoffRequest | None:
    """Build or enrich orchestrator handoff request (routing, type hint, mock flow)."""
    orchestration = parse_orchestration_config(agent_config)
    request = explicit_request
    if not orchestration.handoff_enabled and request is None:
        return None
    resolved_type: AgentType | None = target_type_hint

    if (
        request is None
        and resolved_type is None
        and isinstance(agent_config, dict)
        and agent_config.get("mock_orchestrator_flow") is True
    ):
        resolved_type = resolve_specialist_agent_type(cleaned_payload)

    if request is None and resolved_type is not None:
        target_id = await resolve_project_agent_id_for_type(
            session,
            owner_id=owner_id,
            project_id=project_id,
            agent_type=resolved_type,
        )
        if target_id is None:
            return None
        reason: str | None = None
        if explicit_request is not None and explicit_request.reason:
            reason = explicit_request.reason
        elif isinstance(cleaned_payload.get("goal"), str) and cleaned_payload["goal"].strip():
            reason = str(cleaned_payload["goal"]).strip()[:500]
        request = GraphHandoffRequest(
            target_agent_id=target_id,
            reason=reason,
            options=GraphHandoffOptions(),
        )

    if request is None:
        return None

    return apply_orchestration_handoff_options(request, orchestration)


async def count_parent_handoff_children(
    session: AsyncSession,
    *,
    owner_id: UUID,
    parent_run_id: UUID,
) -> int:
    from app.db.repositories.agent_runs import AgentRunRepository

    return await AgentRunRepository(session).count_handoff_children_for_parent(
        owner_id,
        parent_run_id,
    )


def is_handoff_allowed(source_type: AgentType, target_type: AgentType) -> bool:
    if source_type == target_type:
        return False
    allowed = ALLOWED_HANDOFF_TARGETS.get(source_type, frozenset())
    return target_type in allowed


async def evaluate_graph_handoff(
    session: AsyncSession,
    *,
    owner_id: UUID,
    project_id: UUID,
    source_agent_id: UUID,
    source_agent_type: AgentType,
    request: GraphHandoffRequest | None,
    parent_handoff_depth: int = 0,
) -> GraphHandoffDecision:
    if request is None:
        return GraphHandoffDecision(
            status=HANDOFF_STATUS_NONE,
            target_agent_id=None,
            target_agent_type=None,
            target_agent_name=None,
            reason=None,
            error=None,
            options=GraphHandoffOptions(),
        )

    settings = get_settings()
    if parent_handoff_depth >= settings.graph_handoff_max_depth:
        return GraphHandoffDecision(
            status=HANDOFF_STATUS_REJECTED,
            target_agent_id=None,
            target_agent_type=None,
            target_agent_name=None,
            reason=request.reason if request else None,
            error="handoff_max_depth_exceeded",
            options=request.options,
        )

    if not settings.graph_handoff_enabled:
        return GraphHandoffDecision(
            status=HANDOFF_STATUS_REJECTED,
            target_agent_id=None,
            target_agent_type=None,
            target_agent_name=None,
            reason=request.reason,
            error="graph_handoff_disabled",
            options=request.options,
        )

    if request.target_agent_id == source_agent_id:
        return GraphHandoffDecision(
            status=HANDOFF_STATUS_REJECTED,
            target_agent_id=None,
            target_agent_type=None,
            target_agent_name=None,
            reason=request.reason,
            error="handoff_self_not_allowed",
            options=request.options,
        )

    agents = AgentService(session)
    target = await agents.get_agent(request.target_agent_id, owner_id)
    if target is None or target.status == AgentStatus.ARCHIVED:
        return GraphHandoffDecision(
            status=HANDOFF_STATUS_REJECTED,
            target_agent_id=None,
            target_agent_type=None,
            target_agent_name=None,
            reason=request.reason,
            error="handoff_target_not_found",
            options=request.options,
        )

    if target.project_id != project_id:
        return GraphHandoffDecision(
            status=HANDOFF_STATUS_REJECTED,
            target_agent_id=None,
            target_agent_type=None,
            target_agent_name=None,
            reason=request.reason,
            error="handoff_target_project_mismatch",
            options=request.options,
        )

    if not is_handoff_allowed(source_agent_type, target.type):
        return GraphHandoffDecision(
            status=HANDOFF_STATUS_REJECTED,
            target_agent_id=None,
            target_agent_type=None,
            target_agent_name=None,
            reason=request.reason,
            error="handoff_not_allowed",
            options=request.options,
        )

    return GraphHandoffDecision(
        status=HANDOFF_STATUS_DELEGATED,
        target_agent_id=target.id,
        target_agent_type=target.type.value,
        target_agent_name=target.name,
        reason=request.reason,
        error=None,
        options=request.options,
    )


def build_child_run_input_payload(
    *,
    parent_payload: dict[str, Any],
    decision: GraphHandoffDecision,
    parent_run_id: UUID,
    source_agent_id: UUID,
    source_agent_type: str,
    memory_context: Any | None,
) -> dict[str, Any]:
    prompt_parts: list[str] = []
    parent_prompt = parent_payload.get("prompt")
    if isinstance(parent_prompt, str) and parent_prompt.strip():
        prompt_parts.append(parent_prompt.strip())
    if decision.reason:
        prompt_parts.append(f"Handoff note: {decision.reason}")

    specialist_fields = build_specialist_child_payload(
        decision.target_agent_type,
        parent_payload,
    )
    child_payload: dict[str, Any] = {
        **specialist_fields,
        "prompt": "\n\n".join(prompt_parts) if prompt_parts else "Continue delegated task.",
        "handoff_parent_run_id": str(parent_run_id),
        "handoff_source_agent_id": str(source_agent_id),
        "handoff_source_agent_type": source_agent_type,
    }
    if memory_context is not None:
        child_payload["memory_context"] = memory_context
    sanitized = sanitize_tool_payload(child_payload)
    return sanitized if isinstance(sanitized, dict) else child_payload


def build_child_run_metadata(
    *,
    parent_run_id: UUID,
    trace_id: str,
    handoff_depth: int,
) -> dict[str, Any]:
    return {
        "parent_agent_run_id": str(parent_run_id),
        "handoff_trace_id": trace_id,
        "handoff_depth": handoff_depth,
        "execution_engine": HANDOFF_CHILD_EXECUTION_ENGINE,
    }


async def enqueue_handoff_child_run(
    session: AsyncSession,
    *,
    owner_id: UUID,
    parent_run_id: UUID,
    task_id: UUID | None,
    target_agent_id: UUID,
    parent_payload: dict[str, Any],
    decision: GraphHandoffDecision,
    source_agent_id: UUID,
    source_agent_type: str,
    trace_id: str,
    parent_handoff_depth: int,
    memory_context: Any | None,
    max_child_runs: int | None = None,
) -> GraphHandoffChildResult:
    from app.services.agent_runs import AgentRunService

    settings = get_settings()
    if max_child_runs is not None:
        existing = await count_parent_handoff_children(
            session,
            owner_id=owner_id,
            parent_run_id=parent_run_id,
        )
        if existing >= max_child_runs:
            return GraphHandoffChildResult(
                child_run_id=None,
                child_run_enqueued=False,
                child_run_executed=False,
                child_run_status=None,
                child_run_error="handoff_max_children_exceeded",
            )

    if not settings.graph_handoff_child_run_enabled:
        return GraphHandoffChildResult(
            child_run_id=None,
            child_run_enqueued=False,
            child_run_executed=False,
            child_run_status=None,
            child_run_error=None,
        )

    if not decision.options.enqueue_child:
        return GraphHandoffChildResult(
            child_run_id=None,
            child_run_enqueued=False,
            child_run_executed=False,
            child_run_status=None,
            child_run_error=None,
        )

    child_depth = parent_handoff_depth + 1
    if child_depth > settings.graph_handoff_max_depth:
        return GraphHandoffChildResult(
            child_run_id=None,
            child_run_enqueued=False,
            child_run_executed=False,
            child_run_status=None,
            child_run_error="handoff_max_depth_exceeded",
        )

    child_input = build_child_run_input_payload(
        parent_payload=parent_payload,
        decision=decision,
        parent_run_id=parent_run_id,
        source_agent_id=source_agent_id,
        source_agent_type=source_agent_type,
        memory_context=memory_context,
    )
    child_metadata = build_child_run_metadata(
        parent_run_id=parent_run_id,
        trace_id=trace_id,
        handoff_depth=child_depth,
    )

    agent_runs = AgentRunService(session)
    child_row = await agent_runs.create_run(
        owner_id,
        agent_id=target_agent_id,
        task_id=task_id,
        input_payload=child_input,
        metadata=child_metadata,
    )
    if child_row is None:
        return GraphHandoffChildResult(
            child_run_id=None,
            child_run_enqueued=False,
            child_run_executed=False,
            child_run_status=None,
            child_run_error="handoff_child_create_failed",
        )

    from app.queues.handoff_child_queue import HandoffChildQueue

    executed = False
    child_status: str | None = AgentRunStatus.QUEUED.value
    child_error: str | None = None

    if decision.options.execute_child and settings.graph_handoff_execute_child:
        try:
            finished = await execute_handoff_child_run(
                session,
                owner_id=owner_id,
                run_id=child_row.id,
                agent_runs=agent_runs,
            )
            executed = True
            child_status = finished.status.value
            if finished.error:
                child_error = finished.error
            await _sync_parent_after_child(session, owner_id=owner_id, child_run=finished)
        except Exception as exc:
            executed = True
            child_status = AgentRunStatus.FAILED.value
            child_error = str(exc)[:500]
            failed_child = await agent_runs.get_run(owner_id, child_row.id)
            if failed_child is not None:
                await _sync_parent_after_child(
                    session,
                    owner_id=owner_id,
                    child_run=failed_child,
                )
    else:
        await HandoffChildQueue().enqueue(owner_id, child_row.id)

    return GraphHandoffChildResult(
        child_run_id=child_row.id,
        child_run_enqueued=True,
        child_run_executed=executed,
        child_run_status=child_status,
        child_run_error=child_error,
    )


async def _sync_parent_after_child(
    session: AsyncSession,
    *,
    owner_id: UUID,
    child_run: Any,
) -> None:
    from app.graphs.handoff_sync import sync_parent_handoff_after_child

    await sync_parent_handoff_after_child(
        session,
        owner_id=owner_id,
        child_run=child_run,
    )


async def execute_handoff_child_run(
    session: AsyncSession,
    *,
    owner_id: UUID,
    run_id: UUID,
    agent_runs: Any | None = None,
) -> Any:
    """Execute a queued handoff child run through the LangGraph dry-run path."""
    from app.graphs.runner import AgentGraphRunner
    from app.services.agent_runs import AgentRunService
    from app.services.llm_requests import LLMRequestService

    runs = agent_runs or AgentRunService(session)
    runner = AgentGraphRunner(session, runs, LLMRequestService(session))
    return await runner.execute_run(run_id, owner_id)


def build_handoff_output_payload(
    *,
    source_agent_id: UUID,
    source_agent_type: str,
    decision: GraphHandoffDecision,
    trace_id: str,
    graph_version: str,
    child: GraphHandoffChildResult | None = None,
) -> dict[str, Any]:
    child_result = child or GraphHandoffChildResult(
        child_run_id=None,
        child_run_enqueued=False,
        child_run_executed=False,
        child_run_status=None,
        child_run_error=None,
    )
    return {
        "handoff": {
            "status": decision.status,
            "target_agent_id": str(decision.target_agent_id or ""),
            "target_agent_type": decision.target_agent_type or "",
            "target_agent_name": decision.target_agent_name or "",
            "reason": decision.reason or "",
            "source_agent_id": str(source_agent_id),
            "source_agent_type": source_agent_type,
            "child_run_enqueued": child_result.child_run_enqueued,
            "child_run_id": (
                str(child_result.child_run_id) if child_result.child_run_id else ""
            ),
            "child_run_executed": child_result.child_run_executed,
            "child_run_pending_worker": (
                child_result.child_run_enqueued and not child_result.child_run_executed
            ),
            "child_run_status": child_result.child_run_status or "",
            "child_run_error": child_result.child_run_error or "",
        },
        "execution_engine": "langgraph",
        "trace_id": trace_id,
        "graph_version": graph_version,
    }
