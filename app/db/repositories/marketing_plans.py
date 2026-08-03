"""Marketing plan repository (Phase AI.28)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_plan import MarketingPlanTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import MarketingPlanStatus


class MarketingPlanRepository(BaseRepository[MarketingPlanTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingPlanTable)

    async def get_by_id_for_owner(
        self,
        plan_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingPlanTable | None:
        statement = select(MarketingPlanTable).where(
            MarketingPlanTable.id == plan_id,
            MarketingPlanTable.owner_id == owner_id,
            MarketingPlanTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: MarketingPlanStatus | None = None,
        limit: int = 50,
    ) -> list[MarketingPlanTable]:
        statement = (
            select(MarketingPlanTable)
            .where(
                MarketingPlanTable.owner_id == owner_id,
                MarketingPlanTable.project_id == project_id,
            )
            .order_by(MarketingPlanTable.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(MarketingPlanTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
