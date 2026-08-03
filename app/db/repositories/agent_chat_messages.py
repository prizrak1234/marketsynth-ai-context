"""Chat message repository (Phase AI.1, AI.19)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import (
    AgentChatMessageRole,
    ChatSessionDomain,
)

_LIKE_ESCAPE = "\\"


class ChatMessageRepository(BaseRepository[AgentChatMessageTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentChatMessageTable)

    async def list_for_session(
        self,
        session_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentChatMessageTable]:
        statement = (
            select(AgentChatMessageTable)
            .where(AgentChatMessageTable.session_id == session_id)
            .order_by(AgentChatMessageTable.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_for_session(
        self,
        session_id: UUID,
        *,
        limit: int,
    ) -> list[AgentChatMessageTable]:
        statement = (
            select(AgentChatMessageTable)
            .where(AgentChatMessageTable.session_id == session_id)
            .order_by(AgentChatMessageTable.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def list_preview_messages_for_sessions(
        self,
        session_ids: list[UUID],
        *,
        roles: tuple,
    ) -> list[AgentChatMessageTable]:
        if not session_ids:
            return []
        statement = (
            select(AgentChatMessageTable)
            .where(AgentChatMessageTable.session_id.in_(session_ids))
            .where(AgentChatMessageTable.role.in_(roles))
            .order_by(AgentChatMessageTable.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def search_messages(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        like_pattern: str,
        session_id: UUID | None = None,
        agent_id: UUID | None = None,
        domain: ChatSessionDomain | None = None,
        role: AgentChatMessageRole | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[tuple[AgentChatMessageTable, AgentChatSessionTable]]:
        statement = (
            select(AgentChatMessageTable, AgentChatSessionTable)
            .join(
                AgentChatSessionTable,
                AgentChatMessageTable.session_id == AgentChatSessionTable.id,
            )
            .where(
                AgentChatSessionTable.owner_id == owner_id,
                AgentChatSessionTable.project_id == project_id,
                AgentChatMessageTable.content.ilike(like_pattern, escape=_LIKE_ESCAPE),
            )
        )
        if session_id is not None:
            statement = statement.where(AgentChatMessageTable.session_id == session_id)
        if agent_id is not None:
            statement = statement.where(AgentChatSessionTable.agent_id == agent_id)
        if domain is not None:
            statement = statement.where(AgentChatSessionTable.domain == domain)
        if role is not None:
            statement = statement.where(AgentChatMessageTable.role == role)
        if date_from is not None:
            statement = statement.where(AgentChatMessageTable.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(AgentChatMessageTable.created_at <= date_to)

        statement = (
            statement.order_by(AgentChatMessageTable.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.all())


AgentChatMessageRepository = ChatMessageRepository
