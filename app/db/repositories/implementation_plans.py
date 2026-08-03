"""ImplementationPlan repository (Commercial MVP P1.1)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.db.models.implementation_plan import ImplementationPlanTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import (
    ImplementationPlanLifecycleStatus,
    ImplementationPlanOrigin,
    ImplementationPlanReadinessStatus,
)


class ImplementationPlanRepository(BaseRepository[ImplementationPlanTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ImplementationPlanTable)

    async def get_by_id_for_owner(
        self,
        plan_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ImplementationPlanTable | None:
        statement = select(ImplementationPlanTable).where(
            ImplementationPlanTable.id == plan_id,
            ImplementationPlanTable.owner_id == owner_id,
            ImplementationPlanTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def next_version(self, owner_id: UUID, project_id: UUID) -> int:
        statement = (
            select(ImplementationPlanTable.version)
            .where(
                ImplementationPlanTable.owner_id == owner_id,
                ImplementationPlanTable.project_id == project_id,
            )
            .order_by(desc(ImplementationPlanTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        current = result.scalar_one_or_none()
        return int(current or 0) + 1

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        lifecycle_status: ImplementationPlanLifecycleStatus | None = None,
        readiness_status: ImplementationPlanReadinessStatus | None = None,
        strategy_id: UUID | None = None,
        strategy_version: int | None = None,
        version: int | None = None,
        origin: ImplementationPlanOrigin | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        approved_from: datetime | None = None,
        approved_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ImplementationPlanTable]:
        statement = select(ImplementationPlanTable).where(
            ImplementationPlanTable.owner_id == owner_id,
            ImplementationPlanTable.project_id == project_id,
        )
        if lifecycle_status is not None:
            statement = statement.where(
                ImplementationPlanTable.lifecycle_status == lifecycle_status
            )
        if readiness_status is not None:
            statement = statement.where(
                ImplementationPlanTable.readiness_status == readiness_status
            )
        if strategy_id is not None:
            statement = statement.where(
                ImplementationPlanTable.marketing_strategy_id == strategy_id
            )
        if strategy_version is not None:
            statement = statement.where(
                ImplementationPlanTable.marketing_strategy_version == strategy_version
            )
        if version is not None:
            statement = statement.where(ImplementationPlanTable.version == version)
        if origin is not None:
            statement = statement.where(ImplementationPlanTable.plan_origin == origin)
        if created_from is not None:
            statement = statement.where(ImplementationPlanTable.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(ImplementationPlanTable.created_at <= created_to)
        if approved_from is not None:
            statement = statement.where(
                ImplementationPlanTable.approved_at >= approved_from
            )
        if approved_to is not None:
            statement = statement.where(
                ImplementationPlanTable.approved_at <= approved_to
            )
        statement = (
            statement.order_by(desc(ImplementationPlanTable.version))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def latest_any(
        self, owner_id: UUID, project_id: UUID
    ) -> ImplementationPlanTable | None:
        statement = (
            select(ImplementationPlanTable)
            .where(
                ImplementationPlanTable.owner_id == owner_id,
                ImplementationPlanTable.project_id == project_id,
            )
            .order_by(desc(ImplementationPlanTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
