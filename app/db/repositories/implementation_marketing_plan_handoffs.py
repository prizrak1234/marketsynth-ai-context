"""Repository for Implementation→MarketingPlan handoffs (Commercial MVP P1.2)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.implementation_marketing_plan_handoff import (
    ImplementationMarketingPlanHandoffTable,
)
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import ImplementationMarketingPlanHandoffStatus


class ImplementationMarketingPlanHandoffRepository(
    BaseRepository[ImplementationMarketingPlanHandoffTable]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ImplementationMarketingPlanHandoffTable)

    async def get_by_id_for_owner(
        self,
        handoff_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ImplementationMarketingPlanHandoffTable | None:
        statement = select(ImplementationMarketingPlanHandoffTable).where(
            ImplementationMarketingPlanHandoffTable.id == handoff_id,
            ImplementationMarketingPlanHandoffTable.owner_id == owner_id,
            ImplementationMarketingPlanHandoffTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_fingerprint_any(
        self,
        owner_id: UUID,
        project_id: UUID,
        fingerprint: str,
    ) -> ImplementationMarketingPlanHandoffTable | None:
        statement = select(ImplementationMarketingPlanHandoffTable).where(
            ImplementationMarketingPlanHandoffTable.owner_id == owner_id,
            ImplementationMarketingPlanHandoffTable.project_id == project_id,
            ImplementationMarketingPlanHandoffTable.mapping_fingerprint == fingerprint,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_completed_by_fingerprint(
        self,
        owner_id: UUID,
        project_id: UUID,
        fingerprint: str,
    ) -> ImplementationMarketingPlanHandoffTable | None:
        statement = select(ImplementationMarketingPlanHandoffTable).where(
            ImplementationMarketingPlanHandoffTable.owner_id == owner_id,
            ImplementationMarketingPlanHandoffTable.project_id == project_id,
            ImplementationMarketingPlanHandoffTable.mapping_fingerprint == fingerprint,
            ImplementationMarketingPlanHandoffTable.lifecycle_status
            == ImplementationMarketingPlanHandoffStatus.COMPLETED,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
