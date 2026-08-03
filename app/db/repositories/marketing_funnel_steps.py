"""Marketing funnel step repository (Phase 4.8)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_funnels import MarketingFunnelStepTable
from app.db.repositories.base import BaseRepository
from app.marketing.funnel_contracts import FunnelStepStatus


class MarketingFunnelStepRepository(BaseRepository[MarketingFunnelStepTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingFunnelStepTable)

    async def get_by_id_for_project(
        self,
        step_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingFunnelStepTable | None:
        statement = select(MarketingFunnelStepTable).where(
            MarketingFunnelStepTable.id == step_id,
            MarketingFunnelStepTable.owner_id == owner_id,
            MarketingFunnelStepTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id_for_funnel(
        self,
        step_id: UUID,
        funnel_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingFunnelStepTable | None:
        statement = select(MarketingFunnelStepTable).where(
            MarketingFunnelStepTable.id == step_id,
            MarketingFunnelStepTable.funnel_id == funnel_id,
            MarketingFunnelStepTable.owner_id == owner_id,
            MarketingFunnelStepTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_funnel(
        self,
        funnel_id: UUID,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
    ) -> list[MarketingFunnelStepTable]:
        statement = (
            select(MarketingFunnelStepTable)
            .where(
                MarketingFunnelStepTable.funnel_id == funnel_id,
                MarketingFunnelStepTable.owner_id == owner_id,
                MarketingFunnelStepTable.project_id == project_id,
            )
            .order_by(MarketingFunnelStepTable.position.asc())
        )
        if not include_archived:
            statement = statement.where(
                MarketingFunnelStepTable.status != FunnelStepStatus.ARCHIVED,
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def max_position(self, funnel_id: UUID, owner_id: UUID, project_id: UUID) -> int:
        statement = select(func.max(MarketingFunnelStepTable.position)).where(
            MarketingFunnelStepTable.funnel_id == funnel_id,
            MarketingFunnelStepTable.owner_id == owner_id,
            MarketingFunnelStepTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        value = result.scalar_one_or_none()
        if value is None:
            return 0
        return int(value)

    async def archive(self, row: MarketingFunnelStepTable) -> MarketingFunnelStepTable:
        row.status = FunnelStepStatus.ARCHIVED
        return await self.update(row)
