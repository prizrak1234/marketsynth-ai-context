"""Chat session lifecycle (Phase AI.19)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.agents.direct_specialist.contracts import specialist_domain_for_agent
from app.core.exceptions import InvalidStateError, NotFoundError
from app.core.security import sanitize_text
from app.db.base import utc_now
from app.db.models.agent import AgentTable
from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.repositories.agent_chat_messages import ChatMessageRepository
from app.db.repositories.agent_chat_sessions import ChatSessionRepository
from app.schemas.contracts import (
    AgentChatMessageRole,
    AgentType,
    ChatAuditEventType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionListItem,
    ChatSessionStatus,
)
from app.services.chat_audit_service import ChatAuditService
from app.services.chat_session_preview import (
    SessionMessageUxStats,
    build_preview_from_message,
    empty_session_ux_stats,
)
from app.services.chat_session_title import build_session_title


def resolve_session_entrypoint_and_domain(agent: AgentTable) -> tuple[ChatSessionEntrypoint, ChatSessionDomain]:
    if agent.type == AgentType.GENERAL:
        return ChatSessionEntrypoint.GENERAL_DELEGATION, ChatSessionDomain.UNKNOWN
    specialist_domain = specialist_domain_for_agent(agent.type)
    if specialist_domain == "marketing":
        return ChatSessionEntrypoint.DIRECT_SPECIALIST, ChatSessionDomain.MARKETING
    if specialist_domain == "programmer":
        return ChatSessionEntrypoint.DIRECT_SPECIALIST, ChatSessionDomain.PROGRAMMER
    if specialist_domain == "media":
        return ChatSessionEntrypoint.DIRECT_SPECIALIST, ChatSessionDomain.MEDIA
    return ChatSessionEntrypoint.DIRECT_SPECIALIST, ChatSessionDomain.UNKNOWN


def session_domain_label(domain: ChatSessionDomain) -> str:
    return {
        ChatSessionDomain.UNKNOWN: "General",
        ChatSessionDomain.MARKETING: "Marketing",
        ChatSessionDomain.PROGRAMMER: "Programmer",
        ChatSessionDomain.MEDIA: "Media",
    }.get(domain, domain.value)


class ChatSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = ChatSessionRepository(session)
        self._messages = ChatMessageRepository(session)
        self._audit = ChatAuditService(session)

    async def _load_ux_stats(self, session_ids: list[UUID]) -> dict[UUID, SessionMessageUxStats]:
        if not session_ids:
            return {}

        preview_roles = (AgentChatMessageRole.USER, AgentChatMessageRole.ASSISTANT)
        stats: dict[UUID, SessionMessageUxStats] = {
            session_id: empty_session_ux_stats() for session_id in session_ids
        }

        aggregate_stmt = (
            select(
                AgentChatMessageTable.session_id,
                func.count(AgentChatMessageTable.id).label("message_count"),
                func.max(AgentChatMessageTable.created_at).label("last_message_at"),
            )
            .where(AgentChatMessageTable.session_id.in_(session_ids))
            .where(AgentChatMessageTable.role.in_(preview_roles))
            .group_by(AgentChatMessageTable.session_id)
        )
        aggregate_result = await self._session.execute(aggregate_stmt)
        for row in aggregate_result.all():
            stats[row.session_id] = SessionMessageUxStats(
                message_count=int(row.message_count or 0),
                last_message_at=row.last_message_at,
                last_message_preview=None,
                unread_count=0,
            )

        messages = await self._messages.list_preview_messages_for_sessions(
            session_ids,
            roles=preview_roles,
        )
        preview_set: set[UUID] = set()
        for message in messages:
            if message.session_id in preview_set:
                continue
            preview_set.add(message.session_id)
            prior = stats.get(message.session_id) or empty_session_ux_stats()
            stats[message.session_id] = SessionMessageUxStats(
                message_count=prior.message_count,
                last_message_at=prior.last_message_at,
                last_message_preview=build_preview_from_message(message),
                unread_count=0,
            )

        return stats

    async def get_session(
        self,
        owner_id: UUID,
        project_id: UUID,
        session_id: UUID,
    ) -> AgentChatSessionTable | None:
        return await self._sessions.get_for_project(session_id, owner_id, project_id)

    async def list_sessions(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        agent_id: UUID | None = None,
        status: ChatSessionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentChatSessionTable]:
        effective_status = status if status is not None else ChatSessionStatus.ACTIVE
        return await self._sessions.list_for_project(
            owner_id,
            project_id,
            agent_id=agent_id,
            status=effective_status,
            limit=limit,
            offset=offset,
        )

    async def list_sessions_for_ux(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        agent_id: UUID | None = None,
        status: ChatSessionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ChatSessionListItem]:
        rows = await self.list_sessions(
            owner_id,
            project_id,
            agent_id=agent_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return await self.sessions_to_list_items(rows, status_filter=status)

    async def sessions_to_list_items(
        self,
        rows: list[AgentChatSessionTable],
        *,
        status_filter: ChatSessionStatus | None,
    ) -> list[ChatSessionListItem]:
        stats = await self._load_ux_stats([row.id for row in rows])
        items = [
            self._to_list_item(row, stats.get(row.id) or empty_session_ux_stats())
            for row in rows
        ]
        return self._sort_sessions_for_list(items, status_filter=status_filter)

    @staticmethod
    def _to_list_item(
        row: AgentChatSessionTable,
        stats: SessionMessageUxStats,
    ) -> ChatSessionListItem:
        return ChatSessionListItem(
            id=row.id,
            owner_id=row.owner_id,
            project_id=row.project_id,
            agent_id=row.agent_id,
            entrypoint=row.entrypoint,
            domain=row.domain,
            title=row.title,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_message_preview=stats.last_message_preview,
            last_message_at=stats.last_message_at,
            message_count=stats.message_count,
            unread_count=stats.unread_count,
        )

    @staticmethod
    def _sort_sessions_for_list(
        items: list[ChatSessionListItem],
        *,
        status_filter: ChatSessionStatus | None,
    ) -> list[ChatSessionListItem]:
        def sort_key(item: ChatSessionListItem) -> tuple:
            last_activity = item.last_message_at or item.updated_at
            active_rank = 0 if item.status == ChatSessionStatus.ACTIVE else 1
            if status_filter is not None:
                active_rank = 0
            return (active_rank, -last_activity.timestamp())

        return sorted(items, key=sort_key)

    async def create_session(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        agent: AgentTable,
        first_message: str,
        title: str | None = None,
    ) -> AgentChatSessionTable:
        from app.services.beta_limits_service import BetaLimitsService

        await BetaLimitsService(self._session).assert_can_create_chat_session(
            owner_id,
            project_id,
        )
        entrypoint, domain = resolve_session_entrypoint_and_domain(agent)
        resolved_title = build_session_title(
            first_message=first_message,
            domain=domain,
            provided_title=title,
        )
        created = await self._sessions.create(
            AgentChatSessionTable(
                owner_id=owner_id,
                project_id=project_id,
                agent_id=agent.id,
                entrypoint=entrypoint,
                domain=domain,
                status=ChatSessionStatus.ACTIVE,
                title=resolved_title,
            ),
        )
        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=ChatAuditEventType.SESSION_CREATED,
            status="ok",
            domain=domain,
            entrypoint=entrypoint,
            session_id=created.id,
            agent_id=agent.id,
        )
        return created

    async def ensure_session_continuable(
        self,
        session: AgentChatSessionTable,
        *,
        agent: AgentTable,
        requested_agent_id: UUID | None,
    ) -> None:
        if session.status == ChatSessionStatus.ARCHIVED:
            raise InvalidStateError("Chat session is archived")
        if session.agent_id is not None and requested_agent_id is not None:
            if session.agent_id != requested_agent_id:
                raise InvalidStateError("Chat session belongs to a different agent")
        if session.agent_id is not None and session.agent_id != agent.id:
            raise InvalidStateError("Chat session belongs to a different agent")

    async def archive_session(
        self,
        owner_id: UUID,
        project_id: UUID,
        session_id: UUID,
    ) -> AgentChatSessionTable:
        row = await self._sessions.get_for_project(session_id, owner_id, project_id)
        if row is None:
            raise NotFoundError("Chat session not found")
        row.status = ChatSessionStatus.ARCHIVED
        row.updated_at = utc_now()
        updated = await self._sessions.update(row)
        await self._audit.record(
            owner_id=owner_id,
            project_id=project_id,
            event_type=ChatAuditEventType.SESSION_ARCHIVED,
            status="ok",
            domain=updated.domain,
            entrypoint=updated.entrypoint,
            session_id=updated.id,
            agent_id=updated.agent_id,
        )
        return updated

    async def get_session_message(
        self,
        session_id: UUID,
        message_id: UUID,
    ) -> AgentChatMessageTable | None:
        messages = await self._messages.list_for_session(session_id)
        for row in messages:
            if row.id == message_id:
                return row
        return None

    async def append_user_message(
        self,
        session: AgentChatSessionTable,
        *,
        content: str,
    ) -> AgentChatMessageTable:
        safe_content = sanitize_text(content).strip()
        message = await self._messages.create(
            AgentChatMessageTable(
                session_id=session.id,
                role=AgentChatMessageRole.USER,
                content=safe_content,
                message_metadata={},
            ),
        )
        await self.touch_session(session)
        await self._audit.record(
            owner_id=session.owner_id,
            project_id=session.project_id,
            event_type=ChatAuditEventType.MESSAGE_USER_APPENDED,
            status="ok",
            domain=session.domain,
            entrypoint=session.entrypoint,
            session_id=session.id,
            message_id=message.id,
            agent_id=session.agent_id,
            safe_metadata={"content_length": len(safe_content)},
        )
        return message

    async def append_assistant_message(
        self,
        session: AgentChatSessionTable,
        *,
        content: str,
        agent_run_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> AgentChatMessageTable:
        safe_metadata = metadata if metadata is not None else {}
        safe_content = sanitize_text(content).strip()
        message = await self._messages.create(
            AgentChatMessageTable(
                session_id=session.id,
                role=AgentChatMessageRole.ASSISTANT,
                content=safe_content,
                agent_run_id=agent_run_id,
                message_metadata=safe_metadata,
            ),
        )
        await self.touch_session(session)
        audit_meta: dict = {"content_length": len(safe_content)}
        block_types = safe_metadata.get("block_types")
        if isinstance(block_types, list):
            audit_meta["block_types"] = [str(item) for item in block_types[:20]]
        await self._audit.record(
            owner_id=session.owner_id,
            project_id=session.project_id,
            event_type=ChatAuditEventType.MESSAGE_ASSISTANT_APPENDED,
            status="ok",
            domain=session.domain,
            entrypoint=session.entrypoint,
            session_id=session.id,
            message_id=message.id,
            agent_id=session.agent_id,
            safe_metadata=audit_meta,
        )
        return message

    async def load_recent_history(
        self,
        session_id: UUID,
        *,
        limit: int,
    ) -> list[AgentChatMessageTable]:
        return await self._messages.list_recent_for_session(session_id, limit=limit)

    async def touch_session(self, session: AgentChatSessionTable) -> AgentChatSessionTable:
        session.updated_at = utc_now()
        return await self._sessions.update(session)

    async def maybe_update_session_domain(
        self,
        session: AgentChatSessionTable,
        *,
        domain_value: str,
    ) -> AgentChatSessionTable:
        if session.domain != ChatSessionDomain.UNKNOWN:
            return session
        try:
            session.domain = ChatSessionDomain(domain_value)
        except ValueError:
            return session
        session.updated_at = utc_now()
        return await self._sessions.update(session)
