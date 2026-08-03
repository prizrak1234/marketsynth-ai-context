"""Investigation repository (Commercial MVP P0.2)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.db.models.investigation import InvestigationTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import InvestigationStatus


class InvestigationRepository(BaseRepository[InvestigationTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InvestigationTable)

    async def get_by_id_for_owner(
        self,
        investigation_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> InvestigationTable | None:
        statement = select(InvestigationTable).where(
            InvestigationTable.id == investigation_id,
            InvestigationTable.owner_id == owner_id,
            InvestigationTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: InvestigationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InvestigationTable]:
        statement = select(InvestigationTable).where(
            InvestigationTable.owner_id == owner_id,
            InvestigationTable.project_id == project_id,
        )
        if status is not None:
            statement = statement.where(InvestigationTable.status == status)
        statement = (
            statement.order_by(desc(InvestigationTable.version))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def max_version(self, owner_id: UUID, project_id: UUID) -> int:
        statement = select(InvestigationTable.version).where(
            InvestigationTable.owner_id == owner_id,
            InvestigationTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        versions = list(result.scalars().all())
        return max(versions) if versions else 0

    async def get_active(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> InvestigationTable | None:
        statement = select(InvestigationTable).where(
            InvestigationTable.owner_id == owner_id,
            InvestigationTable.project_id == project_id,
            InvestigationTable.status == InvestigationStatus.ACTIVE,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_any(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> InvestigationTable | None:
        statement = (
            select(InvestigationTable)
            .where(
                InvestigationTable.owner_id == owner_id,
                InvestigationTable.project_id == project_id,
            )
            .order_by(desc(InvestigationTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_prefer_live(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> InvestigationTable | None:
        """Prefer non-terminal investigations, else newest version."""
        live = (
            InvestigationStatus.DRAFT,
            InvestigationStatus.READY,
            InvestigationStatus.ACTIVE,
            InvestigationStatus.BLOCKED,
            InvestigationStatus.UNDER_REVIEW,
        )
        statement = (
            select(InvestigationTable)
            .where(
                InvestigationTable.owner_id == owner_id,
                InvestigationTable.project_id == project_id,
                InvestigationTable.status.in_(live),
            )
            .order_by(desc(InvestigationTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        row = result.scalar_one_or_none()
        if row is not None:
            return row
        return await self.get_latest_any(owner_id, project_id)

    async def get_by_brief_version(
        self,
        owner_id: UUID,
        project_id: UUID,
        project_brief_id: UUID,
        project_brief_version: int,
    ) -> InvestigationTable | None:
        statement = (
            select(InvestigationTable)
            .where(
                InvestigationTable.owner_id == owner_id,
                InvestigationTable.project_id == project_id,
                InvestigationTable.project_brief_id == project_brief_id,
                InvestigationTable.project_brief_version == project_brief_version,
            )
            .order_by(desc(InvestigationTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
