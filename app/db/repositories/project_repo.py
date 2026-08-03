"""Project repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.project import ProjectTable
from app.db.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[ProjectTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectTable)

    async def list_by_owner(self, owner_id: UUID, *, limit: int = 100) -> list[ProjectTable]:
        statement = (
            select(ProjectTable)
            .where(ProjectTable.owner_id == owner_id)
            .order_by(ProjectTable.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
