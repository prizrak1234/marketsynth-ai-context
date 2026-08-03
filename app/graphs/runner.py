"""LangGraph agent run runner — parallel path to AgentRunExecutor."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ExecutorError, InvalidStateError, NotFoundError
from app.db.models.agent_run import AgentRunTable
from app.graphs.agent_graph import get_compiled_agent_graph
from app.graphs.checkpoints import GraphCheckpointStore, InMemoryGraphCheckpointStore
from app.graphs.context import GraphRunContext
from app.graphs.contracts import (
    GRAPH_CONTEXT_CONFIG_KEY,
    AgentGraphState,
    assert_no_graph_state_secrets,
)
from app.llm.config import resolve_llm_config
from app.llm.errors import LLMError, format_llm_error
from app.llm.observability import metrics_from_error
from app.llm.registry import get_llm_adapter
from app.schemas.contracts import AgentRunStatus
from app.services.agent_runs import AgentRunService
from app.services.llm_requests import LLMRequestService
from app.services.tool_execution_log_service import empty_audit_tracker
from app.tools.permissions import build_permission_policy_metadata
from app.tools.registry import get_tool_registry


def _resolve_provider_tools(
    available_tools: list[Any],
    *,
    tools_provider_enabled: bool,
) -> tuple[list[Any] | None, str | None]:
    if not tools_provider_enabled or not available_tools:
        return None, None
    return available_tools, "auto"


class AgentGraphRunner:
    """Execute a queued agent run through a minimal LangGraph state machine."""

    def __init__(
        self,
        session: AsyncSession,
        agent_run_service: AgentRunService,
        llm_request_service: LLMRequestService,
        *,
        checkpoint_store: GraphCheckpointStore | None = None,
    ) -> None:
        self._session = session
        self._agent_runs = agent_run_service
        self._llm_requests = llm_request_service
        self._checkpoint_store = checkpoint_store or InMemoryGraphCheckpointStore()

    @property
    def checkpoint_store(self) -> GraphCheckpointStore:
        return self._checkpoint_store

    async def execute_run(
        self,
        run_id: UUID,
        owner_id: UUID,
        *,
        already_claimed: bool = False,
    ) -> AgentRunTable:
        run = await self._agent_runs.get_run(owner_id, run_id)
        if run is None:
            raise NotFoundError("Agent run not found")

        agent = await self._agent_runs.get_executable_agent(run.agent_id, owner_id)
        if not already_claimed and run.status != AgentRunStatus.QUEUED:
            raise InvalidStateError(f"Agent run is {run.status}, expected queued")
        if already_claimed and run.status != AgentRunStatus.RUNNING:
            raise InvalidStateError(f"Agent run is {run.status}, expected running")

        settings = get_settings()
        provider, model, temperature, max_tokens = resolve_llm_config(agent.config)
        adapter = get_llm_adapter(provider)
        available_tools = get_tool_registry().list_for_agent(agent.type)
        provider_tools, tool_choice = _resolve_provider_tools(
            available_tools,
            tools_provider_enabled=settings.tools_provider_enabled,
        )
        permission_policy = build_permission_policy_metadata(agent.type, available_tools)

        trace_id = str(uuid4())
        graph_state = AgentGraphState.create_initial(
            owner_id=owner_id,
            project_id=run.project_id,
            agent_id=agent.id,
            agent_run_id=run_id,
            task_id=run.task_id,
            input_payload=dict(run.input_payload),
            graph_version=settings.graph_version,
            trace_id=trace_id,
            max_steps=settings.graph_max_steps,
        )
        assert_no_graph_state_secrets(graph_state)

        stored_input_payload = {"input": dict(run.input_payload)}
        prompt_metadata = {
            "executor": "langgraph-dry-run",
            "temperature": temperature,
        }

        graph_context = GraphRunContext(
            session=self._session,
            owner_id=owner_id,
            run_id=run_id,
            agent=agent,
            run=run,
            agent_runs=self._agent_runs,
            llm_requests=self._llm_requests,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            adapter=adapter,
            available_tools=available_tools,
            tool_choice=tool_choice,
            permission_policy=permission_policy,
            provider_tools=provider_tools,
            llm_metadata={"agent_run_id": str(run_id), "executor": "langgraph-dry-run"},
            stored_input_payload=stored_input_payload,
            prompt_metadata=prompt_metadata,
            audit_tracker=empty_audit_tracker(),
            trace_id=trace_id,
            graph_version=settings.graph_version,
            max_steps=settings.graph_max_steps,
            checkpoints_enabled=settings.graph_checkpoints_enabled,
            checkpoint_store=self._checkpoint_store,
        )

        try:
            if not already_claimed:
                claimed_run = await self._agent_runs.claim_queued_run(owner_id, run_id)
                if claimed_run is None:
                    raise InvalidStateError("Agent run is not queued or already claimed")

            graph = get_compiled_agent_graph()
            final_state = await graph.ainvoke(
                graph_state.to_graph_dict(),
                config={
                    "configurable": {
                        GRAPH_CONTEXT_CONFIG_KEY: graph_context,
                    },
                },
            )
            error = final_state.get("error")
            if error:
                raise ExecutorError(str(error))

            final_run = await self._agent_runs.get_run(owner_id, run_id)
            if final_run is None:
                raise RuntimeError("Agent run missing after graph execution")
            return final_run

        except (NotFoundError, InvalidStateError, ConflictError):
            raise
        except ExecutorError:
            raise
        except LLMError as exc:
            safe_error = format_llm_error(exc)
            failure_metadata = metrics_from_error(
                exc,
                latency_ms=exc.latency_ms,
                retry_count=exc.retry_count,
            ).to_metadata()
            failure_metadata["safe_message"] = exc.safe_message
            await self._fail_execution(
                owner_id,
                run_id,
                graph_context.initial_llm_request_id,
                safe_error,
                request_metadata=failure_metadata,
            )
            raise ExecutorError(safe_error) from exc
        except Exception as exc:
            await self._fail_execution(
                owner_id,
                run_id,
                graph_context.initial_llm_request_id,
                str(exc),
            )
            raise ExecutorError(str(exc)) from exc

    async def _fail_execution(
        self,
        owner_id: UUID,
        run_id: UUID,
        llm_request_id: UUID | None,
        error: str,
        *,
        request_metadata: dict[str, Any] | None = None,
    ) -> None:
        if llm_request_id is not None:
            await self._llm_requests.mark_failed(
                owner_id,
                llm_request_id,
                error,
                request_metadata=request_metadata,
            )

        current_run = await self._agent_runs.get_run(owner_id, run_id)
        if current_run is None:
            return
        if current_run.status not in {
            AgentRunStatus.SUCCEEDED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }:
            await self._agent_runs.mark_failed(owner_id, run_id, error)


def is_langgraph_execution_engine() -> bool:
    from app.executors.engine_resolver import resolve_execution_engine

    return resolve_execution_engine(get_settings()) == "langgraph"
