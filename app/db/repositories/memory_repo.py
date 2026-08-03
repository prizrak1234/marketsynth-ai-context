"""Memory item repository — technical system memory, not agent reasoning."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.memory import MemoryItemTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import MemoryLayer


class MemoryRepository(BaseRepository[MemoryItemTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MemoryItemTable)

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        layer: MemoryLayer | None = None,
        limit: int = 100,
    ) -> list[MemoryItemTable]:
        statement = select(MemoryItemTable).where(MemoryItemTable.user_id == user_id)
        if layer is not None:
            statement = statement.where(MemoryItemTable.layer == layer)
        statement = statement.limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_filtered(
        self,
        *,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
        layer: MemoryLayer | None = None,
        limit: int = 100,
    ) -> list[MemoryItemTable]:
        statement = select(MemoryItemTable)
        if user_id is not None:
            statement = statement.where(MemoryItemTable.user_id == user_id)
        if project_id is not None:
            statement = statement.where(MemoryItemTable.project_id == project_id)
        if layer is not None:
            statement = statement.where(MemoryItemTable.layer == layer)
        statement = statement.limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_by_project(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        limit: int = 5,
    ) -> list[MemoryItemTable]:
        statement = (
            select(MemoryItemTable)
            .where(MemoryItemTable.user_id == user_id)
            .where(MemoryItemTable.project_id == project_id)
            .order_by(MemoryItemTable.created_at.desc())
            .limit(min(limit, 10))
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def search_text(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[MemoryItemTable]:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = (
            select(MemoryItemTable)
            .where(MemoryItemTable.user_id == user_id)
            .where(MemoryItemTable.project_id == project_id)
            .where(
                (MemoryItemTable.content.like(pattern, escape="\\"))
                | (MemoryItemTable.key.like(pattern, escape="\\")),
            )
            .limit(min(limit, 20))
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
