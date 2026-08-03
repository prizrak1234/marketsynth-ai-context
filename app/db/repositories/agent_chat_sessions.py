"""Chat session repository (Phase AI.1, AI.19)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select as sqlmodel_select

from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import (
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionStatus,
)

_LIKE_ESCAPE = "\\"


class ChatSessionRepository(BaseRepository[AgentChatSessionTable]):
    """Persisted chat sessions (table: agent_chat_sessions)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentChatSessionTable)

    async def get_for_project(
        self,
        session_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> AgentChatSessionTable | None:
        statement = sqlmodel_select(AgentChatSessionTable).where(
            AgentChatSessionTable.id == session_id,
            AgentChatSessionTable.owner_id == owner_id,
            AgentChatSessionTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        agent_id: UUID | None = None,
        status: ChatSessionStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentChatSessionTable]:
        statement = sqlmodel_select(AgentChatSessionTable).where(
            AgentChatSessionTable.owner_id == owner_id,
            AgentChatSessionTable.project_id == project_id,
        )
        if agent_id is not None:
            statement = statement.where(AgentChatSessionTable.agent_id == agent_id)
        if status is not None:
            statement = statement.where(AgentChatSessionTable.status == status)
        statement = (
            statement.order_by(AgentChatSessionTable.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def search_sessions(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        like_pattern: str | None = None,
        agent_id: UUID | None = None,
        status: ChatSessionStatus | None = None,
        domain: ChatSessionDomain | None = None,
        entrypoint: ChatSessionEntrypoint | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentChatSessionTable]:
        statement = sqlmodel_select(AgentChatSessionTable).where(
            AgentChatSessionTable.owner_id == owner_id,
            AgentChatSessionTable.project_id == project_id,
        )
        if agent_id is not None:
            statement = statement.where(AgentChatSessionTable.agent_id == agent_id)
        if status is not None:
            statement = statement.where(AgentChatSessionTable.status == status)
        if domain is not None:
            statement = statement.where(AgentChatSessionTable.domain == domain)
        if entrypoint is not None:
            statement = statement.where(AgentChatSessionTable.entrypoint == entrypoint)
        if date_from is not None:
            statement = statement.where(AgentChatSessionTable.updated_at >= date_from)
        if date_to is not None:
            statement = statement.where(AgentChatSessionTable.updated_at <= date_to)

        if like_pattern is not None:
            message_match = exists(
                sqlmodel_select(AgentChatMessageTable.id).where(
                    AgentChatMessageTable.session_id == AgentChatSessionTable.id,
                    AgentChatMessageTable.content.ilike(like_pattern, escape=_LIKE_ESCAPE),
                ),
            )
            statement = statement.where(
                or_(
                    AgentChatSessionTable.title.ilike(like_pattern, escape=_LIKE_ESCAPE),
                    message_match,
                ),
            )

        statement = (
            statement.order_by(AgentChatSessionTable.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())


AgentChatSessionRepository = ChatSessionRepository
