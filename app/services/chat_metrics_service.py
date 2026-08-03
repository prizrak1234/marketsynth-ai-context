"""Chat operational metrics (Phase AI.25)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.repositories.chat_audit_events import ChatAuditEventRepository
from app.schemas.agent_chat import AgentChatMetricsResponse
from app.schemas.contracts import (
    AgentChatMessageRole,
    ChatAuditEventType,
    ChatSessionStatus,
)


class ChatMetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = ChatAuditEventRepository(session)

    async def get_project_metrics(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> AgentChatMetricsResponse:
        sessions_total = await self._count_sessions(
            owner_id,
            project_id,
            date_from=date_from,
            date_to=date_to,
        )
        sessions_active = await self._count_sessions(
            owner_id,
            project_id,
            status=ChatSessionStatus.ACTIVE,
            date_from=date_from,
            date_to=date_to,
        )
        sessions_archived = await self._count_sessions(
            owner_id,
            project_id,
            status=ChatSessionStatus.ARCHIVED,
            date_from=date_from,
            date_to=date_to,
        )
        messages_user = await self._count_messages(
            owner_id,
            project_id,
            role=AgentChatMessageRole.USER,
            date_from=date_from,
            date_to=date_to,
        )
        messages_assistant = await self._count_messages(
            owner_id,
            project_id,
            role=AgentChatMessageRole.ASSISTANT,
            date_from=date_from,
            date_to=date_to,
        )
        sessions_by_domain = await self._sessions_by_domain(
            owner_id,
            project_id,
            date_from=date_from,
            date_to=date_to,
        )
        messages_by_domain = await self._messages_by_domain(
            owner_id,
            project_id,
            date_from=date_from,
            date_to=date_to,
        )

        runs_started = await self._audit.count_by_event_types(
            owner_id,
            project_id,
            [ChatAuditEventType.RUN_STARTED],
            date_from=date_from,
            date_to=date_to,
        )
        runs_succeeded = await self._audit.count_by_event_types(
            owner_id,
            project_id,
            [ChatAuditEventType.RUN_SUCCEEDED],
            date_from=date_from,
            date_to=date_to,
        )
        runs_failed = await self._audit.count_by_event_types(
            owner_id,
            project_id,
            [ChatAuditEventType.RUN_FAILED],
            date_from=date_from,
            date_to=date_to,
        )
        block_actions_total = await self._audit.count_by_event_types(
            owner_id,
            project_id,
            [
                ChatAuditEventType.BLOCK_ACTION_REQUESTED,
                ChatAuditEventType.BLOCK_ACTION_SUCCEEDED,
                ChatAuditEventType.BLOCK_ACTION_FAILED,
            ],
            date_from=date_from,
            date_to=date_to,
        )
        block_actions_by_type = await self._audit.count_block_actions_by_type(
            owner_id,
            project_id,
            date_from=date_from,
            date_to=date_to,
        )
        searches_sessions = await self._audit.count_by_event_types(
            owner_id,
            project_id,
            [ChatAuditEventType.SEARCH_SESSIONS],
            date_from=date_from,
            date_to=date_to,
        )
        searches_messages = await self._audit.count_by_event_types(
            owner_id,
            project_id,
            [ChatAuditEventType.SEARCH_MESSAGES],
            date_from=date_from,
            date_to=date_to,
        )

        latest_audit = await self._audit.latest_activity_at(
            owner_id,
            project_id,
            date_from=date_from,
            date_to=date_to,
        )
        latest_message = await self._latest_message_at(
            owner_id,
            project_id,
            date_from=date_from,
            date_to=date_to,
        )
        latest_activity_at = latest_audit
        if latest_message is not None:
            if latest_activity_at is None or latest_message > latest_activity_at:
                latest_activity_at = latest_message

        return AgentChatMetricsResponse(
            sessions_total=sessions_total,
            sessions_active=sessions_active,
            sessions_archived=sessions_archived,
            messages_total=messages_user + messages_assistant,
            messages_user=messages_user,
            messages_assistant=messages_assistant,
            runs_total=runs_started,
            runs_succeeded=runs_succeeded,
            runs_failed=runs_failed,
            block_actions_total=block_actions_total,
            block_actions_by_type=block_actions_by_type,
            searches_total=searches_sessions + searches_messages,
            searches_by_type={
                "sessions": searches_sessions,
                "messages": searches_messages,
            },
            sessions_by_domain=sessions_by_domain,
            messages_by_domain=messages_by_domain,
            latest_activity_at=latest_activity_at,
        )

    async def _count_sessions(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: ChatSessionStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(AgentChatSessionTable)
            .where(
                AgentChatSessionTable.owner_id == owner_id,
                AgentChatSessionTable.project_id == project_id,
            )
        )
        if status is not None:
            statement = statement.where(AgentChatSessionTable.status == status)
        if date_from is not None:
            statement = statement.where(AgentChatSessionTable.updated_at >= date_from)
        if date_to is not None:
            statement = statement.where(AgentChatSessionTable.updated_at <= date_to)
        result = await self._session.execute(statement)
        return int(result.scalar_one() or 0)

    async def _count_messages(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        role: AgentChatMessageRole | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(AgentChatMessageTable)
            .join(
                AgentChatSessionTable,
                AgentChatMessageTable.session_id == AgentChatSessionTable.id,
            )
            .where(
                AgentChatSessionTable.owner_id == owner_id,
                AgentChatSessionTable.project_id == project_id,
            )
        )
        if role is not None:
            statement = statement.where(AgentChatMessageTable.role == role)
        if date_from is not None:
            statement = statement.where(AgentChatMessageTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(AgentChatMessageTable.created_at <= date_to)
        result = await self._session.execute(statement)
        return int(result.scalar_one() or 0)

    async def _sessions_by_domain(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, int]:
        statement = (
            select(AgentChatSessionTable.domain, func.count())
            .where(
                AgentChatSessionTable.owner_id == owner_id,
                AgentChatSessionTable.project_id == project_id,
            )
            .group_by(AgentChatSessionTable.domain)
        )
        if date_from is not None:
            statement = statement.where(AgentChatSessionTable.updated_at >= date_from)
        if date_to is not None:
            statement = statement.where(AgentChatSessionTable.updated_at <= date_to)
        result = await self._session.execute(statement)
        return {str(row[0].value): int(row[1]) for row in result.all()}

    async def _messages_by_domain(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, int]:
        statement = (
            select(AgentChatSessionTable.domain, func.count())
            .select_from(AgentChatMessageTable)
            .join(
                AgentChatSessionTable,
                AgentChatMessageTable.session_id == AgentChatSessionTable.id,
            )
            .where(
                AgentChatSessionTable.owner_id == owner_id,
                AgentChatSessionTable.project_id == project_id,
            )
            .group_by(AgentChatSessionTable.domain)
        )
        if date_from is not None:
            statement = statement.where(AgentChatMessageTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(AgentChatMessageTable.created_at <= date_to)
        result = await self._session.execute(statement)
        return {str(row[0].value): int(row[1]) for row in result.all()}

    async def _latest_message_at(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> datetime | None:
        statement = (
            select(func.max(AgentChatMessageTable.created_at))
            .select_from(AgentChatMessageTable)
            .join(
                AgentChatSessionTable,
                AgentChatMessageTable.session_id == AgentChatSessionTable.id,
            )
            .where(
                AgentChatSessionTable.owner_id == owner_id,
                AgentChatSessionTable.project_id == project_id,
            )
        )
        if date_from is not None:
            statement = statement.where(AgentChatMessageTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(AgentChatMessageTable.created_at <= date_to)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
