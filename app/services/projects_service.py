"""Project business logic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.db.models.project import ProjectTable
from app.db.repositories.project_repo import ProjectRepository
from app.schemas.crud import ProjectCreate, ProjectUpdate
from app.services.beta_limits_service import BetaLimitsService
from app.services.transaction import transactional


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ProjectRepository(session)

    async def create(self, data: ProjectCreate) -> ProjectTable:
        await BetaLimitsService(self._session).assert_can_create_project(data.owner_id)
        async with transactional(self._session):
            row = ProjectTable(**data.model_dump())
            return await self._repo.create(row)

    async def get_by_id(self, project_id: UUID) -> ProjectTable | None:
        return await self._repo.get_by_id(project_id)

    async def list(
        self,
        *,
        user_id: UUID | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ProjectTable]:
        if user_id is not None:
            return await self._repo.list_by_owner(user_id, limit=limit)
        return await self._repo.list(offset=offset, limit=limit)

    async def update(self, project_id: UUID, data: ProjectUpdate) -> ProjectTable | None:
        row = await self._repo.get_by_id(project_id)
        if row is None:
            return None

        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return row

        async with transactional(self._session):
            for field, value in updates.items():
                setattr(row, field, value)
            row.updated_at = utc_now()
            return await self._repo.update(row)

    async def delete(self, project_id: UUID) -> bool:
        row = await self._repo.get_by_id(project_id)
        if row is None:
            return False
        async with transactional(self._session):
            await self._repo.delete(row)
        return True
