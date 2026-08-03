"""ProjectBrief repository (Commercial MVP P0.1)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.db.models.project_brief import ProjectBriefTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import ProjectBriefStatus


class ProjectBriefRepository(BaseRepository[ProjectBriefTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProjectBriefTable)

    async def get_by_id_for_owner(
        self,
        brief_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ProjectBriefTable | None:
        statement = select(ProjectBriefTable).where(
            ProjectBriefTable.id == brief_id,
            ProjectBriefTable.owner_id == owner_id,
            ProjectBriefTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: ProjectBriefStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ProjectBriefTable]:
        statement = select(ProjectBriefTable).where(
            ProjectBriefTable.owner_id == owner_id,
            ProjectBriefTable.project_id == project_id,
        )
        if status is not None:
            statement = statement.where(ProjectBriefTable.status == status)
        statement = (
            statement.order_by(desc(ProjectBriefTable.version))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def max_version(self, owner_id: UUID, project_id: UUID) -> int:
        statement = select(ProjectBriefTable.version).where(
            ProjectBriefTable.owner_id == owner_id,
            ProjectBriefTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        versions = list(result.scalars().all())
        return max(versions) if versions else 0

    async def get_open_draft(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> ProjectBriefTable | None:
        statement = select(ProjectBriefTable).where(
            ProjectBriefTable.owner_id == owner_id,
            ProjectBriefTable.project_id == project_id,
            ProjectBriefTable.status == ProjectBriefStatus.DRAFT,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_submitted(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> ProjectBriefTable | None:
        statement = (
            select(ProjectBriefTable)
            .where(
                ProjectBriefTable.owner_id == owner_id,
                ProjectBriefTable.project_id == project_id,
                ProjectBriefTable.status == ProjectBriefStatus.SUBMITTED,
            )
            .order_by(desc(ProjectBriefTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_any(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> ProjectBriefTable | None:
        statement = (
            select(ProjectBriefTable)
            .where(
                ProjectBriefTable.owner_id == owner_id,
                ProjectBriefTable.project_id == project_id,
            )
            .order_by(desc(ProjectBriefTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def find_submitted_by_fingerprint(
        self,
        owner_id: UUID,
        project_id: UUID,
        fingerprint: str,
    ) -> ProjectBriefTable | None:
        statement = select(ProjectBriefTable).where(
            ProjectBriefTable.owner_id == owner_id,
            ProjectBriefTable.project_id == project_id,
            ProjectBriefTable.status == ProjectBriefStatus.SUBMITTED,
            ProjectBriefTable.input_fingerprint == fingerprint,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
