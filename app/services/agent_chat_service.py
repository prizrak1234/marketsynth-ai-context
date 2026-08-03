"""Agent chat — user message, AgentRun execution, assistant reply (Phase AI.1–AI.7)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.direct_specialist.contracts import (
    DIRECT_SPECIALIST_AGENT_TYPES,
    ENTRYPOINT_DIRECT_SPECIALIST,
    ENTRYPOINT_GENERAL_DELEGATION,
    specialist_domain_for_agent,
)
from app.agents.direct_specialist.execution import (
    build_direct_specialist_run_metadata,
    execute_direct_specialist_chat,
)
from app.agents.general.execution import execute_general_agent
from app.agents.marketer.router import detect_best_subagent
from app.agents.revision_context import build_campaign_revision_context
from app.agents.scenario_context import build_marketing_scenario_context
from app.agents.scenarios.detector import detect_marketing_scenario
from app.core.exceptions import ExecutorError, InvalidStateError, NotFoundError
from app.core.security import sanitize_text
from app.db.models.agent import AgentTable
from app.db.models.agent_chat import AgentChatSessionTable
from app.db.models.chat_audit_event import ChatAuditEventTable
from app.db.repositories.agent_chat_messages import ChatMessageRepository
from app.db.repositories.agent_chat_sessions import ChatSessionRepository
from app.executors.agent_run_coordinator import AgentRunCoordinator
from app.schemas.agent_chat import (
    AgentChatGeneratedAssets,
    AgentChatMessageSearchHit,
    AgentChatMetricsResponse,
    AgentChatPlanDraftCreated,
    AgentChatRevisedAsset,
    ChatAuditEventRead,
    AgentChatExecutionMetadata,
    AgentChatGeneralDelegation,
    AgentChatSendRequest,
    AgentChatSubagentChainEntry,
    AgentChatSubagentExecution,
)
from app.schemas.contracts import (
    AgentChatWorkflowContext,
    AgentRunStatus,
    AgentStatus,
    AgentType,
    ChatAssistantMessageBlock,
    ChatAssistantMessageBlockType,
    ChatAuditEventType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionListItem,
    ChatSessionStatus,
)
from app.services.chat_audit_service import ChatAuditService
from app.services.chat_metrics_service import ChatMetricsService
from app.services.agent_chat_generated_assets import (
    find_generated_assets_from_run,
    format_generate_assets_chat_assistant_message,
    generate_assets_tool_was_executed,
)
from app.services.agent_chat_plan_draft import (
    find_plan_draft_created_by_run,
    format_plan_draft_chat_assistant_message,
    plan_draft_tool_was_executed,
)
from app.services.agent_chat_revision import (
    find_revised_assets_from_run,
    format_revision_chat_assistant_message,
    revision_tool_was_executed,
)
from app.services.agent_chat_run_input import build_agent_chat_run_input_payload
from app.services.agent_runs import AgentRunService
from app.services.chat_session_history import (
    agent_chat_session_history_limit,
    assert_history_safe_for_prompt,
    build_session_history_for_run,
)
from app.services.chat_block_actions import attach_actions_to_blocks
from app.services.chat_history_blocks import rebuild_blocks_for_session_messages
from app.services.chat_search_service import ChatMessageSearchParams, ChatSearchService, ChatSessionSearchParams
from app.services.chat_message_blocks import (
    build_assistant_message_blocks,
    resolve_block_domain,
)
from app.services.chat_session_service import ChatSessionService
from app.services.agents import AgentService
from app.services.campaign_workflow_service import CampaignWorkflowService
from app.services.transaction import transactional
from app.tools.agent_chat_tool_settings import agent_chat_revision_tools_enabled

_AGENT_CHAT_RUN_METADATA = {"agent_chat": True}

@dataclass(frozen=True)
class AgentChatSendResult:
    session: AgentChatSessionTable

    user_message: AgentChatMessageTable

    assistant_message: AgentChatMessageTable

    agent_run_id: UUID

    plan_draft: AgentChatPlanDraftCreated | None = None

    generated_assets: AgentChatGeneratedAssets | None = None

    revised_assets: list[AgentChatRevisedAsset] | None = None

    subagent_execution: AgentChatSubagentExecution | None = None

    subagent_chain: list[AgentChatSubagentChainEntry] | None = None

    general_delegation: AgentChatGeneralDelegation | None = None

    execution_metadata: AgentChatExecutionMetadata | None = None

    blocks: list[ChatAssistantMessageBlock] | None = None

    output: dict[str, object] | None = None


def _build_agent_chat_run_metadata(agent: AgentTable) -> dict[str, object]:
    domain = specialist_domain_for_agent(agent.type)
    if domain is not None:
        return build_direct_specialist_run_metadata(domain=domain)
    return dict(_AGENT_CHAT_RUN_METADATA)


class AgentChatService:
    def __init__(self, session: AsyncSession) -> None:

        self._session = session

        self._sessions = ChatSessionRepository(session)

        self._messages = ChatMessageRepository(session)

        self._chat_sessions = ChatSessionService(session)

        self._agents = AgentService(session)

        self._agent_runs = AgentRunService(session)
        self._audit = ChatAuditService(session)
        self._metrics = ChatMetricsService(session)

    async def get_metrics(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> AgentChatMetricsResponse:
        return await self._metrics.get_project_metrics(
            owner_id,
            project_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def list_audit_events(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        session_id: UUID | None = None,
        event_type: ChatAuditEventType | None = None,
        domain: ChatSessionDomain | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
    ) -> list[ChatAuditEventRead]:
        from app.db.repositories.chat_audit_events import ChatAuditEventRepository

        rows = await ChatAuditEventRepository(self._session).list_for_project(
            owner_id,
            project_id,
            session_id=session_id,
            event_type=event_type,
            domain=domain,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        return [_audit_row_to_read(row) for row in rows]

    async def list_sessions(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        agent_id: UUID | None = None,
        status: ChatSessionStatus | None = None,
        query: str | None = None,
        domain: ChatSessionDomain | None = None,
        entrypoint: ChatSessionEntrypoint | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
    ) -> list[ChatSessionListItem]:
        return await ChatSearchService(self._session).search_sessions(
            owner_id,
            project_id,
            ChatSessionSearchParams(
                query=query,
                agent_id=agent_id,
                status=status,
                domain=domain,
                entrypoint=entrypoint,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
            ),
        )

    async def search_messages(
        self,
        owner_id: UUID,
        project_id: UUID,
        params: ChatMessageSearchParams,
    ) -> list[AgentChatMessageSearchHit]:
        return await ChatSearchService(self._session).search_messages(
            owner_id,
            project_id,
            params,
        )

    async def archive_session(
        self,
        owner_id: UUID,
        project_id: UUID,
        session_id: UUID,
    ) -> AgentChatSessionTable:
        async with transactional(self._session):
            return await self._chat_sessions.archive_session(
                owner_id,
                project_id,
                session_id,
            )

    async def list_messages(
        self,
        owner_id: UUID,
        project_id: UUID,
        session_id: UUID,
        *,
        limit: int = 50,
    ) -> list[AgentChatMessageTable] | None:

        session = await self._sessions.get_for_project(session_id, owner_id, project_id)

        if session is None:
            return None

        return await self._messages.list_for_session(session_id, limit=limit)

    async def list_messages_with_blocks(
        self,
        owner_id: UUID,
        project_id: UUID,
        session_id: UUID,
        *,
        limit: int = 50,
    ) -> tuple[list[AgentChatMessageTable], dict[UUID, list[ChatAssistantMessageBlock]]] | None:
        rows = await self.list_messages(
            owner_id,
            project_id,
            session_id,
            limit=limit,
        )
        if rows is None:
            return None
        blocks_by_id = await rebuild_blocks_for_session_messages(
            self._session,
            owner_id,
            project_id,
            rows,
        )
        return rows, blocks_by_id

    async def send_message(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: AgentChatSendRequest,
    ) -> AgentChatSendResult:

        content = sanitize_text(body.message).strip()

        if not content:
            raise InvalidStateError("Message content is empty after sanitization")

        workflow_context = await self._resolve_workflow_context(
            owner_id,
            project_id,
            body.campaign_id,
        )

        revision_context: dict[str, object] | None = None
        if agent_chat_revision_tools_enabled() and body.campaign_id is not None:
            revision_context = await build_campaign_revision_context(
                self._session,
                owner_id,
                project_id,
                body.campaign_id,
            )

        scenario_context: dict[str, object] | None = None
        if workflow_context is not None:
            workflow_state = str(workflow_context.get("workflow_state", ""))
            scenario_type = detect_marketing_scenario(
                message=content,
                workflow_state=workflow_state,
            )
            scenario_context = build_marketing_scenario_context(
                scenario_type=scenario_type,
                workflow_state=workflow_state,
                next_recommended_action=str(
                    workflow_context.get("next_recommended_action", ""),
                ),
                pending_review_assets=int(workflow_context.get("pending_review_assets", 0) or 0),
            )

        subagent_routing: dict[str, object] | None = None
        selected_subagent = detect_best_subagent(message=content)
        if selected_subagent is not None:
            subagent_routing = {"selected_subagent": selected_subagent.value}

        async with transactional(self._session):
            agent = await self._resolve_agent_for_chat(
                owner_id,
                project_id,
                session_id=body.session_id,
                requested_agent_id=body.agent_id,
            )

            if body.session_id is not None:
                session = await self._chat_sessions.get_session(
                    owner_id,
                    project_id,
                    body.session_id,
                )
                if session is None:
                    raise NotFoundError("Chat session not found")
                await self._chat_sessions.ensure_session_continuable(
                    session,
                    agent=agent,
                    requested_agent_id=body.agent_id,
                )
            else:
                session = await self._chat_sessions.create_session(
                    owner_id,
                    project_id,
                    agent=agent,
                    first_message=content,
                )

            history_limit = agent_chat_session_history_limit()
            prior_messages = await self._chat_sessions.load_recent_history(
                session.id,
                limit=history_limit,
            )
            session_history = build_session_history_for_run(
                prior_messages,
                current_user_content=content,
                limit=history_limit,
            )
            assert_history_safe_for_prompt(session_history)

            input_payload = build_agent_chat_run_input_payload(
                prompt=content,
                project_id=project_id,
                workflow_context=workflow_context,
                revision_context=revision_context,
                scenario_context=scenario_context,
                subagent_routing=subagent_routing,
                session_history=session_history,
            )

            user_message = await self._chat_sessions.append_user_message(
                session,
                content=content,
            )

            run = await self._agent_runs.create_run(
                owner_id,
                agent_id=agent.id,
                task_id=None,
                input_payload=input_payload,
                metadata=_build_agent_chat_run_metadata(agent),
            )

            if run is None:
                raise NotFoundError("Agent not found")

        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=ChatAuditEventType.RUN_STARTED,
            status="started",
            domain=session.domain,
            entrypoint=session.entrypoint,
            session_id=session.id,
            agent_id=agent.id,
            safe_metadata={"agent_run_id": str(run.id)},
        )

        subagent_execution: AgentChatSubagentExecution | None = None
        subagent_chain: list[AgentChatSubagentChainEntry] | None = None
        general_delegation: AgentChatGeneralDelegation | None = None
        execution_metadata: AgentChatExecutionMetadata | None = None
        assistant_content_override: str | None = None

        run_started_at = time.perf_counter()
        try:
            if agent.type == AgentType.GENERAL:
                general_result = await execute_general_agent(
                    self._session,
                    parent_run=run,
                    input_payload=input_payload,
                    owner_id=owner_id,
                    message=content,
                )
                execution_metadata = AgentChatExecutionMetadata(
                    entrypoint=ENTRYPOINT_GENERAL_DELEGATION,
                    domain=general_result.domain.value,
                )
                if general_result.clarification:
                    assistant_content_override = general_result.clarification
                    final_run = run
                else:
                    assert general_result.delegated_child_run is not None
                    general_delegation = AgentChatGeneralDelegation(
                        domain=general_result.domain.value,
                        agent_run_id=general_result.delegated_child_run.id,
                    )
                    subagent_chain = general_result.subagent_chain
                    subagent_execution = general_result.subagent_execution
                    assert general_result.final_run is not None
                    final_run = general_result.final_run
            elif agent.type in DIRECT_SPECIALIST_AGENT_TYPES:
                direct_result = await execute_direct_specialist_chat(
                    self._session,
                    parent_run=run,
                    input_payload=input_payload,
                    owner_id=owner_id,
                    message=content,
                    agent_type=agent.type,
                )
                execution_metadata = AgentChatExecutionMetadata(
                    entrypoint=ENTRYPOINT_DIRECT_SPECIALIST,
                    domain=direct_result.domain,
                )
                if direct_result.clarification:
                    assistant_content_override = direct_result.clarification
                    final_run = run
                else:
                    assert direct_result.final_run is not None
                    final_run = direct_result.final_run
                    subagent_chain = direct_result.subagent_chain
                    subagent_execution = direct_result.subagent_execution
            else:
                final_run, _engine = await AgentRunCoordinator(self._session).execute_run(
                    run.id,
                    owner_id,
                    request_engine="classic",
                )

        except ExecutorError as exc:
            latency_ms = int((time.perf_counter() - run_started_at) * 1000)
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=ChatAuditEventType.RUN_FAILED,
                status="failed",
                domain=session.domain,
                entrypoint=session.entrypoint,
                session_id=session.id,
                agent_id=agent.id,
                safe_metadata={
                    "agent_run_id": str(run.id),
                    "latency_ms": latency_ms,
                    "error_code": "executor_error",
                    "safe_message": "Agent temporarily unavailable",
                },
            )
            raise ExecutorError(
                getattr(exc, "args", ("Agent temporarily unavailable",))[0],
            ) from exc

        latency_ms = int((time.perf_counter() - run_started_at) * 1000)

        if assistant_content_override is not None:
            output: dict[str, object] = {}
        else:
            if final_run.status != AgentRunStatus.SUCCEEDED:
                await self._audit.record(
                    owner_id=owner_id,
                    project_id=project_id,
                    event_type=ChatAuditEventType.RUN_FAILED,
                    status="failed",
                    domain=session.domain,
                    entrypoint=session.entrypoint,
                    session_id=session.id,
                    agent_id=agent.id,
                    safe_metadata={
                        "agent_run_id": str(final_run.id),
                        "latency_ms": latency_ms,
                        "error_code": "run_not_succeeded",
                        "safe_message": "Agent temporarily unavailable",
                    },
                )
                raise ExecutorError("Agent temporarily unavailable")
            output = dict(final_run.output_payload or {})

        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=ChatAuditEventType.RUN_SUCCEEDED,
            status="succeeded",
            domain=session.domain,
            entrypoint=session.entrypoint,
            session_id=session.id,
            agent_id=agent.id,
            safe_metadata={
                "agent_run_id": str(final_run.id),
                "latency_ms": latency_ms,
            },
        )

        llm_content = sanitize_text(str(output.get("content", ""))).strip()

        tools_summary = output.get("tools") if isinstance(output.get("tools"), dict) else {}

        tool_names = (
            list(tools_summary.get("tool_names", [])) if isinstance(tools_summary, dict) else []
        )

        plan_draft = await find_plan_draft_created_by_run(
            self._session,
            owner_id,
            project_id,
            final_run.id,
        )

        generated_assets = await find_generated_assets_from_run(
            self._session,
            owner_id,
            final_run.id,
        )

        revised_assets = await find_revised_assets_from_run(
            self._session,
            owner_id,
            final_run.id,
        )

        if revised_assets:
            assistant_content = format_revision_chat_assistant_message(
                revised_count=len(revised_assets),
            )

        elif generated_assets is not None:
            assistant_content = format_generate_assets_chat_assistant_message(
                created_count=generated_assets.created_count,
                already_generated=generated_assets.already_generated,
            )

        elif plan_draft is not None:
            assistant_content = format_plan_draft_chat_assistant_message(
                draft_id=plan_draft.draft_id,
                campaign_id=plan_draft.campaign_id,
                llm_content=llm_content,
            )

        elif revision_tool_was_executed(tool_names):
            assistant_content = (
                "The revision tool ran but no assets were updated. "
                "Check tool execution logs or try again."
            )

        elif generate_assets_tool_was_executed(tool_names):
            assistant_content = (
                "The generate assets tool ran but no draft assets were persisted. "
                "Check tool execution logs or try again."
            )

        elif plan_draft_tool_was_executed(tool_names):
            assistant_content = (
                "The plan draft tool ran but no draft was persisted. "
                "Check tool execution logs or try again."
            )

        elif assistant_content_override is not None:
            assistant_content = assistant_content_override

        elif llm_content:
            assistant_content = llm_content

        else:
            assistant_content = "I could not generate a response. Please try again."

        block_result = build_assistant_message_blocks(
            output=output,
            execution_metadata=execution_metadata,
            clarification=assistant_content_override,
            plan_draft=plan_draft,
            generated_assets=generated_assets,
            revised_assets=revised_assets or None,
            fallback_text=assistant_content,
        )
        assistant_content = block_result.readable_content
        assistant_metadata = dict(block_result.message_metadata)
        assistant_metadata["source_run_id"] = str(final_run.id)
        response_blocks = list(block_result.blocks)
        response_output = block_result.output
        if not response_blocks and assistant_content:
            domain = resolve_block_domain(execution_metadata)
            response_blocks = attach_actions_to_blocks(
                [
                    ChatAssistantMessageBlock(
                        type=ChatAssistantMessageBlockType.TEXT,
                        domain=domain,
                        content=assistant_content,
                    ),
                ],
            )
            assistant_metadata["block_types"] = ["text"]

        async with transactional(self._session):
            session_row = await self._sessions.get_for_project(session.id, owner_id, project_id)

            if session_row is None:
                raise NotFoundError("Chat session not found")

            if execution_metadata is not None:
                session_row = await self._chat_sessions.maybe_update_session_domain(
                    session_row,
                    domain_value=execution_metadata.domain,
                )

            assistant_message = await self._chat_sessions.append_assistant_message(
                session_row,
                content=assistant_content,
                agent_run_id=final_run.id,
                metadata=assistant_metadata,
            )

        return AgentChatSendResult(
            session=session_row,
            user_message=user_message,
            assistant_message=assistant_message,
            agent_run_id=run.id,
            plan_draft=plan_draft,
            generated_assets=generated_assets,
            revised_assets=revised_assets or None,
            subagent_execution=subagent_execution,
            subagent_chain=subagent_chain,
            general_delegation=general_delegation,
            execution_metadata=execution_metadata,
            blocks=response_blocks,
            output=response_output,
        )

    async def _resolve_agent_for_chat(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        session_id: UUID | None,
        requested_agent_id: UUID | None,
    ) -> AgentTable:
        session_agent_id: UUID | None = None
        if session_id is not None:
            existing = await self._sessions.get_for_project(
                session_id,
                owner_id,
                project_id,
            )
            if existing is None:
                raise NotFoundError("Chat session not found")
            session_agent_id = existing.agent_id

        candidate_ids: list[UUID] = []
        if requested_agent_id is not None:
            candidate_ids.append(requested_agent_id)
        elif session_agent_id is not None:
            candidate_ids.append(session_agent_id)

        for agent_id in candidate_ids:
            agent = await self._agents.get_agent(agent_id, owner_id)
            if (
                agent is not None
                and agent.project_id == project_id
                and agent.status != AgentStatus.ARCHIVED
            ):
                return agent

        agents = await self._agents.list_agents(owner_id, project_id=project_id)
        active = [agent for agent in agents if agent.status == AgentStatus.ACTIVE]
        pool = active or [agent for agent in agents if agent.status != AgentStatus.ARCHIVED]
        if not pool:
            raise NotFoundError("No agent available for chat in this project")
        if agent_chat_revision_tools_enabled() and requested_agent_id is None and session_id is None:
            copywriters = [agent for agent in pool if agent.type == AgentType.COPYWRITER]
            if copywriters:
                return copywriters[0]
        return pool[0]

    async def _resolve_workflow_context(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID | None,
    ) -> dict[str, object] | None:

        if campaign_id is None:
            return None

        workflow = await CampaignWorkflowService(self._session).get_workflow(
            owner_id,
            project_id,
            campaign_id,
        )

        if workflow is None:
            raise NotFoundError("Campaign not found")

        context = AgentChatWorkflowContext(
            campaign_id=workflow.campaign_id,
            workflow_state=workflow.workflow_state,
            next_recommended_action=workflow.next_recommended_action,
            pending_review_assets=workflow.counts.pending_review_assets,
        )

        return context.model_dump(mode="json")


def _audit_row_to_read(row: ChatAuditEventTable) -> ChatAuditEventRead:
    return ChatAuditEventRead(
        id=row.id,
        owner_id=row.owner_id,
        project_id=row.project_id,
        session_id=row.session_id,
        message_id=row.message_id,
        agent_id=row.agent_id,
        event_type=row.event_type,
        domain=row.domain,
        entrypoint=row.entrypoint,
        status=row.status,
        safe_metadata=dict(row.safe_metadata or {}),
        created_at=row.created_at,
    )
