"""MarketingStrategy repository (Commercial MVP P0.6)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.db.models.marketing_strategy import MarketingStrategyTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import (
    MarketingStrategyLifecycleStatus,
    MarketingStrategyOrigin,
    MarketingStrategyReadinessStatus,
)


class MarketingStrategyRepository(BaseRepository[MarketingStrategyTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingStrategyTable)

    async def get_by_id_for_owner(
        self,
        strategy_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingStrategyTable | None:
        statement = select(MarketingStrategyTable).where(
            MarketingStrategyTable.id == strategy_id,
            MarketingStrategyTable.owner_id == owner_id,
            MarketingStrategyTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def next_version(self, owner_id: UUID, project_id: UUID) -> int:
        statement = (
            select(MarketingStrategyTable.version)
            .where(
                MarketingStrategyTable.owner_id == owner_id,
                MarketingStrategyTable.project_id == project_id,
            )
            .order_by(desc(MarketingStrategyTable.version))
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
        lifecycle_status: MarketingStrategyLifecycleStatus | None = None,
        verdict_id: UUID | None = None,
        version: int | None = None,
        readiness_status: MarketingStrategyReadinessStatus | None = None,
        origin: MarketingStrategyOrigin | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        approved_from: datetime | None = None,
        approved_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MarketingStrategyTable]:
        statement = select(MarketingStrategyTable).where(
            MarketingStrategyTable.owner_id == owner_id,
            MarketingStrategyTable.project_id == project_id,
        )
        if lifecycle_status is not None:
            statement = statement.where(
                MarketingStrategyTable.lifecycle_status == lifecycle_status
            )
        if verdict_id is not None:
            statement = statement.where(
                MarketingStrategyTable.business_verdict_id == verdict_id
            )
        if version is not None:
            statement = statement.where(MarketingStrategyTable.version == version)
        if readiness_status is not None:
            statement = statement.where(
                MarketingStrategyTable.readiness_status == readiness_status
            )
        if origin is not None:
            statement = statement.where(MarketingStrategyTable.strategy_origin == origin)
        if created_from is not None:
            statement = statement.where(MarketingStrategyTable.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(MarketingStrategyTable.created_at <= created_to)
        if approved_from is not None:
            statement = statement.where(
                MarketingStrategyTable.approved_at >= approved_from
            )
        if approved_to is not None:
            statement = statement.where(MarketingStrategyTable.approved_at <= approved_to)
        statement = (
            statement.order_by(desc(MarketingStrategyTable.version))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def latest_approved(
        self, owner_id: UUID, project_id: UUID
    ) -> MarketingStrategyTable | None:
        statement = (
            select(MarketingStrategyTable)
            .where(
                MarketingStrategyTable.owner_id == owner_id,
                MarketingStrategyTable.project_id == project_id,
                MarketingStrategyTable.lifecycle_status
                == MarketingStrategyLifecycleStatus.APPROVED,
            )
            .order_by(desc(MarketingStrategyTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def latest_any(
        self, owner_id: UUID, project_id: UUID
    ) -> MarketingStrategyTable | None:
        statement = (
            select(MarketingStrategyTable)
            .where(
                MarketingStrategyTable.owner_id == owner_id,
                MarketingStrategyTable.project_id == project_id,
            )
            .order_by(desc(MarketingStrategyTable.version))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
