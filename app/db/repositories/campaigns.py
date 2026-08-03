"""Business campaign repository (Phase AI.147)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.campaign import CampaignTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import CampaignStatus


class CampaignRepository(BaseRepository[CampaignTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CampaignTable)

    async def get_by_id_for_owner(
        self,
        campaign_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> CampaignTable | None:
        statement = select(CampaignTable).where(
            CampaignTable.id == campaign_id,
            CampaignTable.owner_id == owner_id,
            CampaignTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: CampaignStatus | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[CampaignTable]:
        statement = (
            select(CampaignTable)
            .where(
                CampaignTable.owner_id == owner_id,
                CampaignTable.project_id == project_id,
            )
            .order_by(CampaignTable.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(CampaignTable.status == status)
        if not include_archived:
            statement = statement.where(CampaignTable.status != CampaignStatus.ARCHIVED)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def search(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        query: str | None = None,
        scenario_id: str | None = None,
        status: CampaignStatus | None = None,
        limit: int = 50,
    ) -> list[CampaignTable]:
        statement = select(CampaignTable).where(
            CampaignTable.owner_id == owner_id,
            CampaignTable.project_id == project_id,
        )
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    CampaignTable.name.ilike(pattern),
                    CampaignTable.goal.ilike(pattern),
                ),
            )
        if scenario_id:
            statement = statement.where(CampaignTable.scenario_id == scenario_id)
        if status is not None:
            statement = statement.where(CampaignTable.status == status)
        statement = statement.order_by(CampaignTable.created_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
