"""Campaign workflow run repository (Phase AI.260)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.campaign_workflow_run import CampaignWorkflowRunTable
from app.db.repositories.base import BaseRepository
from app.schemas.contracts import CampaignWorkflowRunStatus


class CampaignWorkflowRunRepository(BaseRepository[CampaignWorkflowRunTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CampaignWorkflowRunTable)

    async def get_by_id_for_owner(
        self,
        run_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> CampaignWorkflowRunTable | None:
        statement = select(CampaignWorkflowRunTable).where(
            CampaignWorkflowRunTable.id == run_id,
            CampaignWorkflowRunTable.owner_id == owner_id,
            CampaignWorkflowRunTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        *,
        limit: int = 20,
    ) -> list[CampaignWorkflowRunTable]:
        statement = (
            select(CampaignWorkflowRunTable)
            .where(
                CampaignWorkflowRunTable.owner_id == owner_id,
                CampaignWorkflowRunTable.project_id == project_id,
                CampaignWorkflowRunTable.campaign_id == campaign_id,
            )
            .order_by(CampaignWorkflowRunTable.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def find_active_for_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
    ) -> CampaignWorkflowRunTable | None:
        active_statuses = (
            CampaignWorkflowRunStatus.DRAFT,
            CampaignWorkflowRunStatus.ACTIVE,
        )
        statement = (
            select(CampaignWorkflowRunTable)
            .where(
                CampaignWorkflowRunTable.owner_id == owner_id,
                CampaignWorkflowRunTable.project_id == project_id,
                CampaignWorkflowRunTable.campaign_id == campaign_id,
                CampaignWorkflowRunTable.status.in_(active_statuses),
            )
            .order_by(CampaignWorkflowRunTable.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def has_non_archived_for_template(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        template_id: str,
    ) -> bool:
        statement = select(CampaignWorkflowRunTable.id).where(
            CampaignWorkflowRunTable.owner_id == owner_id,
            CampaignWorkflowRunTable.project_id == project_id,
            CampaignWorkflowRunTable.campaign_id == campaign_id,
            CampaignWorkflowRunTable.template_id == template_id,
            CampaignWorkflowRunTable.status != CampaignWorkflowRunStatus.ARCHIVED,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None
