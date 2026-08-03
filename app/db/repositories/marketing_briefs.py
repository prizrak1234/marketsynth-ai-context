"""Marketing brief repository (Phase 4.0)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing import MarketingBriefTable
from app.db.repositories.base import BaseRepository
from app.marketing.contracts import MarketingBriefStatus


class MarketingBriefRepository(BaseRepository[MarketingBriefTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingBriefTable)

    async def get_by_id_for_owner(
        self,
        brief_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingBriefTable | None:
        statement = select(MarketingBriefTable).where(
            MarketingBriefTable.id == brief_id,
            MarketingBriefTable.owner_id == owner_id,
            MarketingBriefTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        status: MarketingBriefStatus | None = None,
        limit: int = 100,
    ) -> list[MarketingBriefTable]:
        statement = (
            select(MarketingBriefTable)
            .where(
                MarketingBriefTable.owner_id == owner_id,
                MarketingBriefTable.project_id == project_id,
            )
            .order_by(MarketingBriefTable.created_at.desc())
            .limit(limit)
        )
        if not include_archived:
            statement = statement.where(
                MarketingBriefTable.status != MarketingBriefStatus.ARCHIVED,
            )
        if status is not None:
            statement = statement.where(MarketingBriefTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def archive(self, row: MarketingBriefTable) -> MarketingBriefTable:
        row.status = MarketingBriefStatus.ARCHIVED
        return await self.update(row)
