"""Campaign plan draft repository (Phase 10.1)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.campaign_plan_drafts import CampaignPlanDraftTable
from app.db.repositories.base import BaseRepository
from app.marketing.contracts import CampaignPlanDraftStatus


class CampaignPlanDraftRepository(BaseRepository[CampaignPlanDraftTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CampaignPlanDraftTable)

    async def get_by_id_for_campaign(
        self,
        draft_id: UUID,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignPlanDraftTable | None:
        statement = select(CampaignPlanDraftTable).where(
            CampaignPlanDraftTable.id == draft_id,
            CampaignPlanDraftTable.owner_id == owner_id,
            CampaignPlanDraftTable.project_id == project_id,
            CampaignPlanDraftTable.campaign_id == campaign_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CampaignPlanDraftTable]:
        statement = select(CampaignPlanDraftTable).where(
            CampaignPlanDraftTable.owner_id == owner_id,
            CampaignPlanDraftTable.project_id == project_id,
            CampaignPlanDraftTable.campaign_id == campaign_id,
        )
        if not include_archived:
            statement = statement.where(
                CampaignPlanDraftTable.status != CampaignPlanDraftStatus.ARCHIVED,
            )
        statement = (
            statement.order_by(CampaignPlanDraftTable.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def archive(self, row: CampaignPlanDraftTable) -> CampaignPlanDraftTable:
        row.status = CampaignPlanDraftStatus.ARCHIVED
        return await self.update(row)
