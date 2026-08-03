"""Marketing campaign repository (Phase 9.0)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ContentAssetTable
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.models.publishing import PublicationJobTable
from app.db.repositories.base import BaseRepository
from app.marketing.contracts import ContentAssetStatus, MarketingCampaignStatus
from app.publishing.contracts import PublicationJobStatus


class MarketingCampaignRepository(BaseRepository[MarketingCampaignTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketingCampaignTable)

    async def get_by_id_for_project(
        self,
        campaign_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MarketingCampaignTable | None:
        statement = select(MarketingCampaignTable).where(
            MarketingCampaignTable.id == campaign_id,
            MarketingCampaignTable.owner_id == owner_id,
            MarketingCampaignTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[MarketingCampaignTable]:
        statement = (
            select(MarketingCampaignTable)
            .where(
                MarketingCampaignTable.owner_id == owner_id,
                MarketingCampaignTable.project_id == project_id,
            )
            .order_by(MarketingCampaignTable.created_at.desc())
            .limit(limit)
        )
        if not include_archived:
            statement = statement.where(
                MarketingCampaignTable.status != MarketingCampaignStatus.ARCHIVED,
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        status: MarketingCampaignStatus | None = None,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketingCampaignTable]:
        statement = select(MarketingCampaignTable).where(
            MarketingCampaignTable.owner_id == owner_id,
            MarketingCampaignTable.project_id == project_id,
        )
        if status is not None:
            statement = statement.where(MarketingCampaignTable.status == status)
        if not include_archived:
            statement = statement.where(
                MarketingCampaignTable.status != MarketingCampaignStatus.ARCHIVED,
            )
        statement = (
            statement.order_by(MarketingCampaignTable.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def archive(self, row: MarketingCampaignTable) -> MarketingCampaignTable:
        row.status = MarketingCampaignStatus.ARCHIVED
        return await self.update(row)

    async def operational_metrics_counts(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> dict[str, int]:
        """Aggregate campaign operational metrics (Phase 9.3). Counts only — no metadata."""
        base = select(MarketingCampaignTable.status, func.count()).where(
            MarketingCampaignTable.owner_id == owner_id,
        )
        if project_id is not None:
            base = base.where(MarketingCampaignTable.project_id == project_id)
        base = base.group_by(MarketingCampaignTable.status)
        result = await self.session.execute(base)
        by_status = {
            status.value if hasattr(status, "value") else str(status): int(count)
            for status, count in result.all()
        }

        counts = {
            "total": sum(by_status.values()),
            "draft": by_status.get(MarketingCampaignStatus.DRAFT.value, 0),
            "active": by_status.get(MarketingCampaignStatus.ACTIVE.value, 0),
            "paused": by_status.get(MarketingCampaignStatus.PAUSED.value, 0),
            "completed": by_status.get(MarketingCampaignStatus.COMPLETED.value, 0),
            "archived": by_status.get(MarketingCampaignStatus.ARCHIVED.value, 0),
            "active_with_scheduled_jobs": await self._count_active_with_scheduled_jobs(
                owner_id=owner_id,
                project_id=project_id,
            ),
            "active_without_approved_assets": await self._count_active_without_approved_assets(
                owner_id=owner_id,
                project_id=project_id,
            ),
        }
        return counts

    async def _count_active_with_scheduled_jobs(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> int:
        scheduled_job_exists = (
            select(PublicationJobTable.id)
            .where(
                PublicationJobTable.owner_id == owner_id,
                PublicationJobTable.campaign_id == MarketingCampaignTable.id,
                PublicationJobTable.status == PublicationJobStatus.SCHEDULED,
            )
            .correlate(MarketingCampaignTable)
        )
        if project_id is not None:
            scheduled_job_exists = scheduled_job_exists.where(
                PublicationJobTable.project_id == project_id,
            )

        statement = select(func.count()).where(
            MarketingCampaignTable.owner_id == owner_id,
            MarketingCampaignTable.status == MarketingCampaignStatus.ACTIVE,
            exists(scheduled_job_exists),
        )
        if project_id is not None:
            statement = statement.where(MarketingCampaignTable.project_id == project_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def _count_active_without_approved_assets(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> int:
        approved_asset_exists = (
            select(ContentAssetTable.id)
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.campaign_id == MarketingCampaignTable.id,
                ContentAssetTable.status == ContentAssetStatus.APPROVED,
            )
            .correlate(MarketingCampaignTable)
        )
        if project_id is not None:
            approved_asset_exists = approved_asset_exists.where(
                ContentAssetTable.project_id == project_id,
            )

        statement = select(func.count()).where(
            MarketingCampaignTable.owner_id == owner_id,
            MarketingCampaignTable.status == MarketingCampaignStatus.ACTIVE,
            ~exists(approved_asset_exists),
        )
        if project_id is not None:
            statement = statement.where(MarketingCampaignTable.project_id == project_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())

