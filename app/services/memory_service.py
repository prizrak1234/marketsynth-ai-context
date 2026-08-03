"""Memory item business logic — technical system memory, not agent reasoning."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.memory import MemoryItemTable
from app.db.models.task import TaskTable
from app.db.repositories.memory_repo import MemoryRepository
from app.schemas.contracts import MemoryLayer
from app.schemas.crud import MemoryItemCreate, MemoryItemUpdate
from app.services.transaction import transactional


class MemoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MemoryRepository(session)

    async def create(self, data: MemoryItemCreate) -> MemoryItemTable:
        async with transactional(self._session):
            payload = data.model_dump()
            metadata = payload.pop("metadata")
            row = MemoryItemTable(**payload, item_metadata=metadata)
            return await self._repo.create(row)

    async def get_by_id(self, memory_item_id: UUID) -> MemoryItemTable | None:
        return await self._repo.get_by_id(memory_item_id)

    async def list(
        self,
        *,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
        agent_id: UUID | None = None,
        layer: MemoryLayer | None = None,
        limit: int = 100,
    ) -> list[MemoryItemTable]:
        if agent_id is not None:
            task_result = await self._session.execute(
                select(TaskTable.project_id).where(TaskTable.agent_id == agent_id).distinct(),
            )
            project_ids = [row[0] for row in task_result.all()]
            if not project_ids:
                return []

            rows: list[MemoryItemTable] = []
            for pid in project_ids:
                rows.extend(
                    await self._repo.list_filtered(
                        user_id=user_id,
                        project_id=pid,
                        layer=layer,
                        limit=limit,
                    ),
                )
            return rows[:limit]

        return await self._repo.list_filtered(
            user_id=user_id,
            project_id=project_id,
            layer=layer,
            limit=limit,
        )

    async def search(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        query: str,
        agent_id: UUID | None = None,
        limit: int = 5,
    ) -> list[MemoryItemTable]:
        del agent_id  # reserved for future task-scoped filtering
        return await self._repo.search_text(
            user_id=user_id,
            project_id=project_id,
            query=query,
            limit=min(limit, 20),
        )

    async def update(
        self,
        memory_item_id: UUID,
        data: MemoryItemUpdate,
    ) -> MemoryItemTable | None:
        row = await self._repo.get_by_id(memory_item_id)
        if row is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return row

        async with transactional(self._session):
            metadata = updates.pop("metadata", None)
            for field, value in updates.items():
                setattr(row, field, value)
            if metadata is not None:
                row.item_metadata = metadata
            return await self._repo.update(row)

    async def delete(self, memory_item_id: UUID) -> bool:
        row = await self._repo.get_by_id(memory_item_id)
        if row is None:
            return False
        async with transactional(self._session):
            await self._repo.delete(row)
        return True
