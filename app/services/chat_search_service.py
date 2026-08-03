"""Chat search orchestration (Phase AI.24)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.agent_chat_messages import ChatMessageRepository
from app.db.repositories.agent_chat_sessions import ChatSessionRepository
from app.schemas.agent_chat import AgentChatMessageSearchHit
from app.schemas.contracts import (
    AgentChatMessageRole,
    ChatAuditEventType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionListItem,
    ChatSessionStatus,
)
from app.services.chat_audit_service import ChatAuditService
from app.services.chat_search import (
    build_like_pattern,
    build_search_content_preview,
    prepare_search_query,
)
from app.services.chat_session_service import ChatSessionService


@dataclass(frozen=True)
class ChatSessionSearchParams:
    query: str | None = None
    agent_id: UUID | None = None
    status: ChatSessionStatus | None = None
    domain: ChatSessionDomain | None = None
    entrypoint: ChatSessionEntrypoint | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class ChatMessageSearchParams:
    query: str
    session_id: UUID | None = None
    agent_id: UUID | None = None
    domain: ChatSessionDomain | None = None
    role: AgentChatMessageRole | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 20
    offset: int = 0


class ChatSearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_search = ChatSessionRepository(session)
        self._message_search = ChatMessageRepository(session)
        self._chat_sessions = ChatSessionService(session)
        self._audit = ChatAuditService(session)

    async def search_sessions(
        self,
        owner_id: UUID,
        project_id: UUID,
        params: ChatSessionSearchParams,
    ) -> list[ChatSessionListItem]:
        cleaned_query = prepare_search_query(params.query, required=False)
        like_pattern = build_like_pattern(cleaned_query) if cleaned_query else None

        effective_status = params.status if params.status is not None else ChatSessionStatus.ACTIVE
        fetch_limit = min(max(params.limit * 3, params.limit), 100) if like_pattern else params.limit

        rows = await self._session_search.search_sessions(
            owner_id,
            project_id,
            like_pattern=like_pattern,
            agent_id=params.agent_id,
            status=effective_status,
            domain=params.domain,
            entrypoint=params.entrypoint,
            date_from=params.date_from,
            date_to=params.date_to,
            limit=fetch_limit,
            offset=params.offset,
        )

        sorted_items = await self._chat_sessions.sessions_to_list_items(
            rows,
            status_filter=params.status,
        )
        result = sorted_items[: params.limit]
        if cleaned_query is not None:
            await self._audit.record(
                owner_id=owner_id,
                project_id=project_id,
                event_type=ChatAuditEventType.SEARCH_SESSIONS,
                status="ok",
                domain=ChatSessionDomain.UNKNOWN,
                entrypoint=ChatSessionEntrypoint.DIRECT_SPECIALIST,
                safe_metadata={
                    "query_length": len(cleaned_query),
                    "result_count": len(result),
                },
            )
        return result

    async def search_messages(
        self,
        owner_id: UUID,
        project_id: UUID,
        params: ChatMessageSearchParams,
    ) -> list[AgentChatMessageSearchHit]:
        cleaned_query = prepare_search_query(params.query, required=True)
        like_pattern = build_like_pattern(cleaned_query)

        rows = await self._message_search.search_messages(
            owner_id,
            project_id,
            like_pattern=like_pattern,
            session_id=params.session_id,
            agent_id=params.agent_id,
            domain=params.domain,
            role=params.role,
            date_from=params.date_from,
            date_to=params.date_to,
            limit=params.limit,
            offset=params.offset,
        )

        hits: list[AgentChatMessageSearchHit] = []
        for message, session_row in rows:
            hits.append(
                AgentChatMessageSearchHit(
                    message_id=message.id,
                    session_id=session_row.id,
                    session_title=session_row.title,
                    role=message.role,
                    content_preview=build_search_content_preview(message.content),
                    created_at=message.created_at,
                    domain=session_row.domain,
                    entrypoint=session_row.entrypoint,
                ),
            )
        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=ChatAuditEventType.SEARCH_MESSAGES,
            status="ok",
            domain=params.domain or ChatSessionDomain.UNKNOWN,
            entrypoint=ChatSessionEntrypoint.DIRECT_SPECIALIST,
            session_id=params.session_id,
            safe_metadata={
                "query_length": len(cleaned_query),
                "result_count": len(hits),
            },
        )
        return hits
