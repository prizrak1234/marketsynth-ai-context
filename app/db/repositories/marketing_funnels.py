"""Marketing funnel repository (Phase 4.8)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_funnels import MarketingFunnelTable
from app.db.repositories.base import BaseRepository
from app.marketing.funnel_contracts import MarketingFunnelStatus


class MarketingFunnelRepository(BaseRepository[MarketingFunnelTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingFunnelTable)

    async def get_by_id_for_project(
        self,
        funnel_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingFunnelTable | None:
        statement = select(MarketingFunnelTable).where(
            MarketingFunnelTable.id == funnel_id,
            MarketingFunnelTable.owner_id == owner_id,
            MarketingFunnelTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        status: MarketingFunnelStatus | None = None,
        limit: int = 100,
    ) -> list[MarketingFunnelTable]:
        statement = (
            select(MarketingFunnelTable)
            .where(
                MarketingFunnelTable.owner_id == owner_id,
                MarketingFunnelTable.project_id == project_id,
            )
            .order_by(MarketingFunnelTable.created_at.desc())
            .limit(limit)
        )
        if not include_archived:
            statement = statement.where(
                MarketingFunnelTable.status != MarketingFunnelStatus.ARCHIVED,
            )
        if status is not None:
            statement = statement.where(MarketingFunnelTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def archive(self, row: MarketingFunnelTable) -> MarketingFunnelTable:
        row.status = MarketingFunnelStatus.ARCHIVED
        return await self.update(row)
