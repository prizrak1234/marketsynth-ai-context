"""Repository for commercial next-step decisions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.commercial_next_step_decision import CommercialNextStepDecisionTable


class CommercialNextStepDecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        row: CommercialNextStepDecisionTable,
    ) -> CommercialNextStepDecisionTable:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_idempotency_key(
        self,
        owner_id: UUID,
        idempotency_key: str,
    ) -> CommercialNextStepDecisionTable | None:
        stmt = select(CommercialNextStepDecisionTable).where(
            CommercialNextStepDecisionTable.owner_id == owner_id,
            CommercialNextStepDecisionTable.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_verdict(
        self,
        owner_id: UUID,
        business_verdict_id: UUID,
    ) -> CommercialNextStepDecisionTable | None:
        stmt = (
            select(CommercialNextStepDecisionTable)
            .where(
                CommercialNextStepDecisionTable.owner_id == owner_id,
                CommercialNextStepDecisionTable.business_verdict_id == business_verdict_id,
            )
            .order_by(CommercialNextStepDecisionTable.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
    ) -> CommercialNextStepDecisionTable | None:
        stmt = (
            select(CommercialNextStepDecisionTable)
            .where(
                CommercialNextStepDecisionTable.owner_id == owner_id,
                CommercialNextStepDecisionTable.project_id == project_id,
            )
            .order_by(CommercialNextStepDecisionTable.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
