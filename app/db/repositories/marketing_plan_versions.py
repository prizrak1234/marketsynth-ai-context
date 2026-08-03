"""Marketing plan version repository (Phase AI.28)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_plan import MarketingPlanVersionTable
from app.db.repositories.base import BaseRepository


class MarketingPlanVersionRepository(BaseRepository[MarketingPlanVersionTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingPlanVersionTable)

    async def list_for_plan(
        self,
        marketing_plan_id: UUID,
        *,
        limit: int = 100,
    ) -> list[MarketingPlanVersionTable]:
        statement = (
            select(MarketingPlanVersionTable)
            .where(MarketingPlanVersionTable.marketing_plan_id == marketing_plan_id)
            .order_by(MarketingPlanVersionTable.version_number.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_version(
        self,
        marketing_plan_id: UUID,
        version_number: int,
    ) -> MarketingPlanVersionTable | None:
        statement = select(MarketingPlanVersionTable).where(
            MarketingPlanVersionTable.marketing_plan_id == marketing_plan_id,
            MarketingPlanVersionTable.version_number == version_number,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
