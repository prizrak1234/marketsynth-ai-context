"""Dry-run agent run executor — LLM adapter registry, no LangGraph."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ExecutorError, InvalidStateError, NotFoundError
from app.db.models.agent_run import AgentRunTable
from app.llm.config import resolve_llm_config, validate_llm_request_payload
from app.llm.contracts import LLMGenerateInput, LLMGenerateOutput, LLMMessage
from app.llm.errors import LLMError, format_llm_error
from app.llm.observability import metrics_from_error, metrics_from_output
from app.llm.registry import get_llm_adapter
from app.llm.run_metadata import build_llm_run_metadata
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.prompts.safety import PromptBuildError
from app.schemas.contracts import AgentRunStatus
from app.services.agent_runs import AgentRunService
from app.services.llm_requests import LLMRequestService
from app.services.memory_service import MemoryService
from app.services.tool_execution_log_service import ToolExecutionLogService, empty_audit_tracker
from app.tools.context_budget import apply_tool_results_context_budget
from app.tools.contracts import ToolExecutionContext, ToolResult
from app.tools.executor import (
    SafeNoOpToolExecutor,
    build_tool_call_limit_exceeded_result,
    build_tool_call_metadata,
    build_tools_run_summary,
    enrich_tool_round_metadata,
)
from app.tools.permissions import build_permission_policy_metadata
from app.tools.agent_chat_tool_settings import list_tools_for_agent_chat
from app.tools.registry import get_tool_registry
from app.tools.result_messages import build_assistant_tool_call_message, build_tool_result_message


def _cost_estimate(output: LLMGenerateOutput) -> float | None:
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


def _initial_tools_metadata(
    available_tools: list[Any],
    *,
    tool_choice: str | None = None,
    permission_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_tool_call_metadata(
        available_tool_names=[tool.name for tool in available_tools],
        tool_results=[],
        tool_choice=tool_choice,
        permission_policy=permission_policy,
    )


def _resolve_provider_tools(
    available_tools: list[Any],
    *,
    tools_provider_enabled: bool,
) -> tuple[list[Any] | None, str | None]:
    if not tools_provider_enabled or not available_tools:
        return None, None
    return available_tools, "auto"


def _build_llm_metadata(
    run_id: UUID,
    *,
    agent: Any = None,
    input_payload: dict[str, Any] | None = None,
    mock_tool_call: Any = None,
    debug_tool_call: Any = None,
    force_tool_call: Any = None,
) -> dict[str, Any]:
    agent_type = getattr(agent, "type", None) if agent is not None else None
    agent_config = getattr(agent, "config", None) if agent is not None else None
    return build_llm_run_metadata(
        run_id,
        agent_type=agent_type,
        agent_config=agent_config if isinstance(agent_config, dict) else None,
        input_payload=input_payload,
        mock_tool_call=mock_tool_call,
        debug_tool_call=debug_tool_call,
        force_tool_call=force_tool_call,
    )


class AgentRunExecutor:
    def __init__(
        self,
        session: AsyncSession,
        agent_run_service: AgentRunService,
        llm_request_service: LLMRequestService,
    ) -> None:
        self._session = session
        self._agent_runs = agent_run_service
        self._llm_requests = llm_request_service

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

        provider, model, temperature, max_tokens = resolve_llm_config(agent.config)
        adapter = get_llm_adapter(provider)

        (
            input_payload,
            memory_context,
            user_context,
            mock_tool_call,
            debug_tool_call,
            force_tool_call,
        ) = _extract_prompt_payload(run.input_payload)

        llm_request_id: UUID | None = None
        try:
            prompt_build = build_llm_messages(
                PromptBuildInput(
                    agent_id=agent.id,
                    agent_type=agent.type,
                    agent_config=agent.config,
                    input_payload=input_payload,
                    memory_context=memory_context,
                    user_context=user_context,
                ),
            )
            messages = prompt_build.messages
            run_metadata = dict(run.run_metadata or {})
            if run_metadata.get("agent_chat"):
                available_tools = list_tools_for_agent_chat(get_tool_registry(), agent.type)
            else:
                available_tools = get_tool_registry().list_for_agent(agent.type)
            settings = get_settings()
            provider_tools, tool_choice = _resolve_provider_tools(
                available_tools,
                tools_provider_enabled=settings.tools_provider_enabled,
            )
            permission_policy = build_permission_policy_metadata(agent.type, available_tools)
            tools_metadata = _initial_tools_metadata(
                available_tools,
                tool_choice=tool_choice,
                permission_policy=permission_policy,
            )

            llm_metadata = _build_llm_metadata(
                run_id,
                agent=agent,
                input_payload=input_payload,
                mock_tool_call=mock_tool_call,
                debug_tool_call=debug_tool_call,
                force_tool_call=force_tool_call,
            )

            if not already_claimed:
                claimed_run = await self._agent_runs.claim_queued_run(owner_id, run_id)
                if claimed_run is None:
                    raise InvalidStateError("Agent run is not queued or already claimed")

            stored_input_payload = {
                "input": input_payload,
            }
            prompt_metadata = {
                "executor": "dry-run",
                "temperature": temperature,
                **prompt_build.metadata,
            }
            request_metadata = {
                "executor": "dry-run",
                "max_tokens": max_tokens,
                "provider": provider.value,
                "model": model,
                "tools_metadata": tools_metadata,
                **prompt_build.metadata,
            }
            validate_llm_request_payload(
                input_payload=stored_input_payload,
                prompt_metadata=prompt_metadata,
                request_metadata=request_metadata,
            )

            llm_request = await self._llm_requests.create_request(
                owner_id,
                agent_run_id=run_id,
                provider=provider,
                model=model,
                input_payload=stored_input_payload,
                prompt_metadata=prompt_metadata,
                request_metadata=request_metadata,
            )
            if llm_request is None:
                raise RuntimeError("Failed to create LLM request")

            llm_request_id = llm_request.id

            running_request = await self._llm_requests.mark_running(owner_id, llm_request_id)
            if running_request is None:
                raise RuntimeError("Failed to mark LLM request running")

            llm_output = await adapter.generate(
                LLMGenerateInput(
                    provider=provider,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=provider_tools,
                    tool_choice=tool_choice,
                    metadata=llm_metadata,
                ),
            )

            if not llm_output.tool_calls:
                return await self._complete_single_llm_call(
                    owner_id=owner_id,
                    run_id=run_id,
                    llm_request_id=llm_request_id,
                    llm_output=llm_output,
                    model=model,
                    prompt_build_metadata=prompt_build.metadata,
                    tools_metadata=tools_metadata,
                )

            return await self._complete_tool_round(
                owner_id=owner_id,
                run_id=run_id,
                agent=agent,
                run=run,
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                adapter=adapter,
                messages=messages,
                llm_request_id=llm_request_id,
                initial_output=llm_output,
                available_tools=available_tools,
                tool_choice=tool_choice,
                permission_policy=permission_policy,
                prompt_build_metadata=prompt_build.metadata,
                stored_input_payload=stored_input_payload,
                prompt_metadata=prompt_metadata,
            )

        except (NotFoundError, InvalidStateError, ConflictError, PromptBuildError):
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
            failure_metadata.update(prompt_build.metadata)
            await self._fail_execution(
                owner_id,
                run_id,
                llm_request_id,
                safe_error,
                request_metadata=failure_metadata,
            )
            raise ExecutorError(safe_error) from exc
        except Exception as exc:
            await self._fail_execution(owner_id, run_id, llm_request_id, str(exc))
            raise ExecutorError(str(exc)) from exc

    async def _complete_single_llm_call(
        self,
        *,
        owner_id: UUID,
        run_id: UUID,
        llm_request_id: UUID,
        llm_output: LLMGenerateOutput,
        model: str,
        prompt_build_metadata: dict[str, Any],
        tools_metadata: dict[str, Any],
    ) -> AgentRunTable:
        observability = metrics_from_output(llm_output).to_metadata()
        succeeded = await self._llm_requests.mark_succeeded(
            owner_id,
            llm_request_id,
            output_payload={
                "content": llm_output.content,
                "provider": llm_output.provider.value,
                "model": llm_output.model or model,
            },
            raw_response={},
            input_tokens=int(llm_output.usage.get("input_tokens", 0)),
            output_tokens=int(llm_output.usage.get("output_tokens", 0)),
            total_tokens=int(llm_output.usage.get("total_tokens", 0)),
            cost_estimate=_cost_estimate(llm_output),
            latency_ms=llm_output.latency_ms or 0,
            response_metadata={
                "executor": "dry-run",
                "tools_metadata": tools_metadata,
                **observability,
            },
            request_metadata_update={
                **prompt_build_metadata,
                **observability,
                "tools_metadata": tools_metadata,
            },
        )
        if succeeded is None or succeeded.response is None:
            raise RuntimeError("Failed to complete LLM request")

        output_payload: dict[str, Any] = {
            "content": llm_output.content,
            "llm_request_id": str(llm_request_id),
            "llm_response_id": str(succeeded.response.id),
            "provider": llm_output.provider.value,
            "model": llm_output.model or model,
            "latency_ms": llm_output.latency_ms,
            "retry_count": llm_output.retry_count,
        }
        final_run = await self._agent_runs.mark_succeeded(owner_id, run_id, output_payload)
        if final_run is None:
            raise RuntimeError("Failed to mark agent run succeeded")
        return final_run

    async def _complete_tool_round(
        self,
        *,
        owner_id: UUID,
        run_id: UUID,
        agent: Any,
        run: AgentRunTable,
        provider: Any,
        model: str,
        temperature: float | None,
        max_tokens: int | None,
        adapter: Any,
        messages: list[LLMMessage],
        llm_request_id: UUID,
        initial_output: LLMGenerateOutput,
        available_tools: list[Any],
        tool_choice: str | None,
        permission_policy: dict[str, Any],
        prompt_build_metadata: dict[str, Any],
        stored_input_payload: dict[str, Any],
        prompt_metadata: dict[str, Any],
    ) -> AgentRunTable:
        tool_context = ToolExecutionContext(
            owner_id=owner_id,
            project_id=run.project_id,
            agent_id=agent.id,
            agent_type=agent.type,
            agent_run_id=run_id,
            task_id=run.task_id,
            request_id=llm_request_id,
            audit_tracker=empty_audit_tracker(),
        )
        audit_service = ToolExecutionLogService(self._session)
        noop_executor = SafeNoOpToolExecutor(
            get_tool_registry(),
            memory_service=MemoryService(self._session),
            audit_service=audit_service,
            session=self._session,
        )
        all_tool_calls = list(initial_output.tool_calls or [])
        max_tool_calls = get_settings().max_tool_calls_per_round
        accepted_calls = all_tool_calls[:max_tool_calls]
        excess_calls = all_tool_calls[max_tool_calls:]

        tool_results: list[ToolResult] = []
        for tool_call in accepted_calls:
            result = await noop_executor.execute(tool_call, tool_context)
            tool_results.append(result)
        for tool_call in excess_calls:
            tool_results.append(build_tool_call_limit_exceeded_result(tool_call))

        budgeted_tool_results = apply_tool_results_context_budget(tool_results)

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

        first_observability = metrics_from_output(initial_output).to_metadata()
        first_succeeded = await self._llm_requests.mark_succeeded(
            owner_id,
            llm_request_id,
            output_payload={
                "content": initial_output.content,
                "provider": initial_output.provider.value,
                "model": initial_output.model or model,
                "finish_reason": initial_output.finish_reason,
                "tool_calls_detected": len(initial_output.tool_calls or []),
            },
            raw_response={},
            input_tokens=int(initial_output.usage.get("input_tokens", 0)),
            output_tokens=int(initial_output.usage.get("output_tokens", 0)),
            total_tokens=int(initial_output.usage.get("total_tokens", 0)),
            cost_estimate=_cost_estimate(initial_output),
            latency_ms=initial_output.latency_ms or 0,
            response_metadata={
                "executor": "dry-run",
                "phase": "initial",
                "tools_metadata": tools_metadata,
                **first_observability,
            },
            request_metadata_update={
                **prompt_build_metadata,
                **first_observability,
                "tools_metadata": tools_metadata,
            },
        )
        if first_succeeded is None or first_succeeded.response is None:
            raise RuntimeError("Failed to complete initial LLM request")

        follow_up_messages = list(messages)
        follow_up_messages.append(
            build_assistant_tool_call_message(
                initial_output.tool_calls or [],
                content=initial_output.content or None,
            ),
        )
        for tool_call, tool_result in zip(
            initial_output.tool_calls or [],
            budgeted_tool_results,
            strict=True,
        ):
            follow_up_messages.append(build_tool_result_message(tool_call, tool_result))

        follow_up_request_metadata = {
            "executor": "dry-run",
            "max_tokens": max_tokens,
            "provider": provider.value,
            "model": model,
            "phase": "tool_follow_up",
            "parent_request_id": str(llm_request_id),
            "tools_metadata": tools_metadata,
            **prompt_build_metadata,
        }
        validate_llm_request_payload(
            input_payload=stored_input_payload,
            prompt_metadata=prompt_metadata,
            request_metadata=follow_up_request_metadata,
        )

        follow_up_request = await self._llm_requests.create_request(
            owner_id,
            agent_run_id=run_id,
            provider=provider,
            model=model,
            input_payload=stored_input_payload,
            prompt_metadata=prompt_metadata,
            request_metadata=follow_up_request_metadata,
        )
        if follow_up_request is None:
            raise RuntimeError("Failed to create follow-up LLM request")

        follow_up_request_id = follow_up_request.id
        running_follow_up = await self._llm_requests.mark_running(owner_id, follow_up_request_id)
        if running_follow_up is None:
            raise RuntimeError("Failed to mark follow-up LLM request running")

        follow_up_metadata = build_llm_run_metadata(
            run_id,
            agent_type=agent.type,
            agent_config=agent.config if isinstance(agent.config, dict) else None,
            input_payload=stored_input_payload.get("input")
            if isinstance(stored_input_payload.get("input"), dict)
            else None,
        )
        follow_up_metadata["phase"] = "tool_follow_up"

        follow_up_output = await adapter.generate(
            LLMGenerateInput(
                provider=provider,
                model=model,
                messages=follow_up_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=None,
                tool_choice=None,
                metadata=follow_up_metadata,
            ),
        )

        if follow_up_output.tool_calls:
            nested_metadata = enrich_tool_round_metadata(
                tools_metadata,
                tool_rounds=1,
                follow_up_llm_call=True,
                nested_tool_calls=True,
            )
            error = "nested_tool_calls_not_supported"
            await self._llm_requests.mark_failed(
                owner_id,
                follow_up_request_id,
                error,
                request_metadata={
                    **follow_up_request_metadata,
                    "tools_metadata": nested_metadata,
                },
            )
            await self._agent_runs.mark_failed(owner_id, run_id, error)
            raise ExecutorError(error)

        follow_up_observability = metrics_from_output(follow_up_output).to_metadata()
        follow_up_succeeded = await self._llm_requests.mark_succeeded(
            owner_id,
            follow_up_request_id,
            output_payload={
                "content": follow_up_output.content,
                "provider": follow_up_output.provider.value,
                "model": follow_up_output.model or model,
                "finish_reason": follow_up_output.finish_reason,
            },
            raw_response={},
            input_tokens=int(follow_up_output.usage.get("input_tokens", 0)),
            output_tokens=int(follow_up_output.usage.get("output_tokens", 0)),
            total_tokens=int(follow_up_output.usage.get("total_tokens", 0)),
            cost_estimate=_cost_estimate(follow_up_output),
            latency_ms=follow_up_output.latency_ms or 0,
            response_metadata={
                "executor": "dry-run",
                "phase": "tool_follow_up",
                "tools_metadata": tools_metadata,
                **follow_up_observability,
            },
            request_metadata_update={
                **prompt_build_metadata,
                **follow_up_observability,
                "tools_metadata": tools_metadata,
            },
        )
        if follow_up_succeeded is None or follow_up_succeeded.response is None:
            raise RuntimeError("Failed to complete follow-up LLM request")

        audit_summary = (
            tool_context.audit_tracker.to_summary()
            if tool_context.audit_tracker is not None
            else {"logged_count": 0, "failed_to_log_count": 0}
        )
        output_payload: dict[str, Any] = {
            "content": follow_up_output.content,
            "llm_request_id": str(follow_up_request_id),
            "llm_response_id": str(follow_up_succeeded.response.id),
            "provider": follow_up_output.provider.value,
            "model": follow_up_output.model or model,
            "latency_ms": follow_up_output.latency_ms,
            "retry_count": follow_up_output.retry_count,
            "initial_llm_request_id": str(llm_request_id),
            "tool_rounds": 1,
            "follow_up_llm_call": True,
            "tool_audit": audit_summary,
            "tools": build_tools_run_summary(tool_results),
        }
        final_run = await self._agent_runs.mark_succeeded(owner_id, run_id, output_payload)
        if final_run is None:
            raise RuntimeError("Failed to mark agent run succeeded")
        return final_run

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
