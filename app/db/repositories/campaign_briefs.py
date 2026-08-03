"""Campaign brief repository (Phase AI.211)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.campaign_brief import CampaignBriefTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import CampaignBriefStatus


class CampaignBriefRepository(BaseRepository[CampaignBriefTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CampaignBriefTable)

    async def get_by_id_for_owner(
        self,
        brief_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> CampaignBriefTable | None:
        statement = select(CampaignBriefTable).where(
            CampaignBriefTable.id == brief_id,
            CampaignBriefTable.owner_id == owner_id,
            CampaignBriefTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_confirmed_for_campaign(
        self,
        campaign_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> CampaignBriefTable | None:
        statement = select(CampaignBriefTable).where(
            CampaignBriefTable.campaign_id == campaign_id,
            CampaignBriefTable.owner_id == owner_id,
            CampaignBriefTable.project_id == project_id,
            CampaignBriefTable.status == CampaignBriefStatus.CONFIRMED,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
