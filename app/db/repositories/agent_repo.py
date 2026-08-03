"""Agent repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.agent import AgentTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import AgentStatus


class AgentRepository(BaseRepository[AgentTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentTable)

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        project_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[AgentTable]:
        statement = select(AgentTable).where(AgentTable.owner_id == owner_id)
        if project_id is not None:
            statement = statement.where(AgentTable.project_id == project_id)
        if not include_archived:
            statement = statement.where(AgentTable.status != AgentStatus.ARCHIVED)
        statement = statement.order_by(AgentTable.created_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[AgentTable]:
        statement = select(AgentTable).where(AgentTable.project_id == project_id)
        if owner_id is not None:
            statement = statement.where(AgentTable.owner_id == owner_id)
        if not include_archived:
            statement = statement.where(AgentTable.status != AgentStatus.ARCHIVED)
        statement = statement.order_by(AgentTable.created_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_for_owner(self, agent_id: UUID, owner_id: UUID) -> AgentTable | None:
        statement = select(AgentTable).where(
            AgentTable.id == agent_id,
            AgentTable.owner_id == owner_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
