"""Agent chat API (Phase AI.1)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import agent_chat_message_to_contract, agent_chat_session_to_contract
from app.core.exceptions import ConflictError, ExecutorError, InvalidStateError, NotFoundError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.agent_chat import (
    AgentChatMessageSearchHit,
    AgentChatMetricsResponse,
    AgentChatSendRequest,
    AgentChatSendResponse,
    ChatAuditEventRead,
    ChatBlockActionRequest,
    ChatBlockActionResponse,
)
from app.schemas.contracts import (
    AgentChatMessage,
    AgentChatMessageRole,
    AgentChatSession,
    AgentChatSessionListItem,
    ChatAuditEventType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionStatus,
)
from app.services.agent_chat_service import AgentChatService
from app.services.chat_block_action_service import ChatBlockActionService

router = APIRouter(
    prefix="/projects/{project_id}/agent-chat",
    tags=["agent-chat"],
)


@router.post("", response_model=AgentChatSendResponse, status_code=status.HTTP_200_OK)
async def send_agent_chat_message(
    body: AgentChatSendRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentChatSendResponse:
    service = AgentChatService(session)
    try:
        result = await service.send_message(
            current_user.id,
            project.id,
            body,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ExecutorError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent temporarily unavailable",
        ) from exc
    return AgentChatSendResponse(
        session=agent_chat_session_to_contract(result.session),
        session_id=result.session.id,
        user_message=agent_chat_message_to_contract(result.user_message),
        assistant_message=agent_chat_message_to_contract(result.assistant_message),
        assistant_message_id=result.assistant_message.id,
        agent_run_id=result.agent_run_id,
        plan_draft=result.plan_draft,
        generated_assets=result.generated_assets,
        revised_assets=result.revised_assets,
        subagent_execution=result.subagent_execution,
        subagent_chain=result.subagent_chain,
        general_delegation=result.general_delegation,
        execution_metadata=result.execution_metadata,
        output=result.output or {},
        blocks=result.blocks or [],
    )


@router.post(
    "/block-actions",
    response_model=ChatBlockActionResponse,
    status_code=status.HTTP_200_OK,
)
async def execute_chat_block_action(
    body: ChatBlockActionRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ChatBlockActionResponse:
    service = ChatBlockActionService(session)
    try:
        result = await service.execute(
            current_user.id,
            project.id,
            session_id=body.session_id,
            assistant_message_id=body.assistant_message_id,
            block_index=body.block_index,
            action_type=body.action_type,
            payload=body.payload,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidStateError, ConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ChatBlockActionResponse(
        status=result.status,
        message=result.message,
        created_resource_type=result.created_resource_type,
        created_resource_id=result.created_resource_id,
        text=result.text,
        markdown=result.markdown,
    )


@router.get("/sessions", response_model=list[AgentChatSessionListItem])
async def list_agent_chat_sessions(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    query: str | None = Query(default=None, max_length=120),
    agent_id: UUID | None = None,
    status: ChatSessionStatus | None = None,
    domain: ChatSessionDomain | None = None,
    entrypoint: ChatSessionEntrypoint | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[AgentChatSessionListItem]:
    service = AgentChatService(session)
    try:
        return await service.list_sessions(
            current_user.id,
            project.id,
            query=query,
            agent_id=agent_id,
            status=status,
            domain=domain,
            entrypoint=entrypoint,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
    except InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/search-messages", response_model=list[AgentChatMessageSearchHit])
async def search_agent_chat_messages(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    query: str = Query(..., min_length=1, max_length=120),
    session_id: UUID | None = None,
    agent_id: UUID | None = None,
    domain: ChatSessionDomain | None = None,
    role: AgentChatMessageRole | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> list[AgentChatMessageSearchHit]:
    from app.services.chat_search_service import ChatMessageSearchParams

    service = AgentChatService(session)
    try:
        return await service.search_messages(
            current_user.id,
            project.id,
            ChatMessageSearchParams(
                query=query,
                session_id=session_id,
                agent_id=agent_id,
                domain=domain,
                role=role,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
            ),
        )
    except InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/sessions/{session_id}/archive",
    response_model=AgentChatSession,
    status_code=status.HTTP_200_OK,
)
async def archive_agent_chat_session(
    session_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> AgentChatSession:
    service = AgentChatService(session)
    try:
        row = await service.archive_session(current_user.id, project.id, session_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return agent_chat_session_to_contract(row)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[AgentChatMessage],
)
async def list_agent_chat_messages(
    session_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[AgentChatMessage]:
    service = AgentChatService(session)
    result = await service.list_messages_with_blocks(
        current_user.id,
        project.id,
        session_id,
        limit=limit,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    rows, blocks_by_id = result
    return [
        agent_chat_message_to_contract(row, blocks=blocks_by_id.get(row.id, []))
        for row in rows
    ]


@router.get("/metrics", response_model=AgentChatMetricsResponse)
async def get_agent_chat_metrics(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> AgentChatMetricsResponse:
    service = AgentChatService(session)
    return await service.get_metrics(
        current_user.id,
        project.id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/audit-events", response_model=list[ChatAuditEventRead])
async def list_agent_chat_audit_events(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    session_id: UUID | None = None,
    event_type: ChatAuditEventType | None = None,
    domain: ChatSessionDomain | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ChatAuditEventRead]:
    service = AgentChatService(session)
    return await service.list_audit_events(
        current_user.id,
        project.id,
        session_id=session_id,
        event_type=event_type,
        domain=domain,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
