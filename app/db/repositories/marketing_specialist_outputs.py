"""Marketing specialist output repository (Phase AI.30)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing_specialist_output import MarketingSpecialistOutputTable
from app.db.repositories.base import BaseRepository
from app.db.repositories.enum_filters import enum_column_equals
from app.schemas.contracts import (
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)


class MarketingSpecialistOutputRepository(BaseRepository[MarketingSpecialistOutputTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingSpecialistOutputTable)

    async def get_by_id_for_owner(
        self,
        output_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingSpecialistOutputTable | None:
        statement = select(MarketingSpecialistOutputTable).where(
            MarketingSpecialistOutputTable.id == output_id,
            MarketingSpecialistOutputTable.owner_id == owner_id,
            MarketingSpecialistOutputTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_run_and_task_index(
        self,
        execution_run_id: UUID,
        task_index: int,
    ) -> MarketingSpecialistOutputTable | None:
        statement = select(MarketingSpecialistOutputTable).where(
            MarketingSpecialistOutputTable.execution_run_id == execution_run_id,
            MarketingSpecialistOutputTable.task_index == task_index,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        execution_run_id: UUID | None = None,
        marketing_plan_id: UUID | None = None,
        specialist: MarketingSpecialistType | None = None,
        status: MarketingSpecialistOutputStatus | None = None,
        limit: int = 50,
    ) -> list[MarketingSpecialistOutputTable]:
        statement = (
            select(MarketingSpecialistOutputTable)
            .where(
                MarketingSpecialistOutputTable.owner_id == owner_id,
                MarketingSpecialistOutputTable.project_id == project_id,
            )
            .order_by(MarketingSpecialistOutputTable.created_at.desc())
            .limit(limit)
        )
        if execution_run_id is not None:
            statement = statement.where(
                MarketingSpecialistOutputTable.execution_run_id == execution_run_id,
            )
        if marketing_plan_id is not None:
            statement = statement.where(
                MarketingSpecialistOutputTable.marketing_plan_id == marketing_plan_id,
            )
        if specialist is not None:
            statement = statement.where(
                enum_column_equals(MarketingSpecialistOutputTable.specialist, specialist),
            )
        if status is not None:
            statement = statement.where(
                enum_column_equals(MarketingSpecialistOutputTable.status, status),
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
