"""Task repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.project import ProjectTable
from app.db.models.task import TaskTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import TaskStatus


class TaskRepository(BaseRepository[TaskTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TaskTable)

    async def list_by_project(self, project_id: UUID, *, limit: int = 100) -> list[TaskTable]:
        statement = select(TaskTable).where(TaskTable.project_id == project_id).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        limit: int = 5,
        status: TaskStatus | None = None,
    ) -> list[TaskTable]:
        statement = (
            select(TaskTable)
            .join(ProjectTable, TaskTable.project_id == ProjectTable.id)
            .where(
                TaskTable.project_id == project_id,
                ProjectTable.owner_id == owner_id,
            )
            .order_by(TaskTable.created_at.desc())
            .limit(min(limit, 10))
        )
        if status is not None:
            statement = statement.where(TaskTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        task_id: UUID,
    ) -> TaskTable | None:
        statement = (
            select(TaskTable)
            .join(ProjectTable, TaskTable.project_id == ProjectTable.id)
            .where(
                TaskTable.id == task_id,
                TaskTable.project_id == project_id,
                ProjectTable.owner_id == owner_id,
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
