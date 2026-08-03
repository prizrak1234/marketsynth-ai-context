"""Task business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.task import TaskTable
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.task_repo import TaskRepository
from app.schemas.contracts import AgentStatus
from app.schemas.crud import TaskCreate, TaskUpdate
from app.services.agents import AgentService
from app.services.transaction import transactional


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TaskRepository(session)

    async def create(self, data: TaskCreate) -> TaskTable:
        async with transactional(self._session):
            row = TaskTable(**data.model_dump())
            return await self._repo.create(row)

    async def get_by_id(self, task_id: UUID) -> TaskTable | None:
        return await self._repo.get_by_id(task_id)

    async def list(
        self,
        *,
        project_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[TaskTable]:
        if project_id is not None:
            return await self._repo.list_by_project(project_id, limit=limit)
        return await self._repo.list(offset=offset, limit=limit)

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        project_id: UUID | None = None,
        limit: int = 100,
    ) -> list[TaskTable]:
        project_repo = ProjectRepository(self._session)
        if project_id is not None:
            project = await project_repo.get_by_id(project_id)
            if project is None or project.owner_id != user_id:
                return []
            return await self._repo.list_by_project(project_id, limit=limit)

        projects = await project_repo.list_by_owner(user_id, limit=1000)
        rows: list[TaskTable] = []
        for project in projects:
            rows.extend(await self._repo.list_by_project(project.id, limit=limit))
        return rows[:limit]

    async def validate_agent_assignment(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        agent_id: UUID | None,
    ) -> bool:
        if agent_id is None:
            return True
        agent = await AgentService(self._session).get_agent(agent_id, owner_id)
        if agent is None or agent.project_id != project_id:
            return False
        return agent.status != AgentStatus.ARCHIVED

    async def update(self, task_id: UUID, data: TaskUpdate) -> TaskTable | None:
        row = await self._repo.get_by_id(task_id)
        if row is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return row

        async with transactional(self._session):
            for field, value in updates.items():
                setattr(row, field, value)
            return await self._repo.update(row)

    async def delete(self, task_id: UUID) -> bool:
        row = await self._repo.get_by_id(task_id)
        if row is None:
            return False
        async with transactional(self._session):
            await self._repo.delete(row)
        return True
