"""Marketing plan execution run repository (Phase AI.29)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_plan_execution_run import MarketingPlanExecutionRunTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import MarketingPlanExecutionStatus


class MarketingPlanExecutionRunRepository(BaseRepository[MarketingPlanExecutionRunTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingPlanExecutionRunTable)

    async def get_by_id_for_owner(
        self,
        run_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingPlanExecutionRunTable | None:
        statement = select(MarketingPlanExecutionRunTable).where(
            MarketingPlanExecutionRunTable.id == run_id,
            MarketingPlanExecutionRunTable.owner_id == owner_id,
            MarketingPlanExecutionRunTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        marketing_plan_id: UUID | None = None,
        status: MarketingPlanExecutionStatus | None = None,
        limit: int = 50,
    ) -> list[MarketingPlanExecutionRunTable]:
        statement = (
            select(MarketingPlanExecutionRunTable)
            .where(
                MarketingPlanExecutionRunTable.owner_id == owner_id,
                MarketingPlanExecutionRunTable.project_id == project_id,
            )
            .order_by(MarketingPlanExecutionRunTable.created_at.desc())
            .limit(limit)
        )
        if marketing_plan_id is not None:
            statement = statement.where(
                MarketingPlanExecutionRunTable.marketing_plan_id == marketing_plan_id,
            )
        if status is not None:
            statement = statement.where(MarketingPlanExecutionRunTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
