"""Campaign overview read model (Phase 9.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mappers import marketing_campaign_to_contract, publication_job_to_contract
from app.db.models.marketing import ContentAssetTable
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.models.publication_delivery_log import PublicationDeliveryLogTable
from app.db.models.publishing import PublicationJobTable
from app.marketing.contracts import ContentAssetStatus
from app.publishing.contracts import PublicationDeliveryLogStatus, PublicationJobStatus
from app.schemas.marketing_campaigns import (
    CampaignOverviewCounts,
    CampaignOverviewResponse,
    CampaignOverviewSchedule,
)


class CampaignOverviewService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_overview(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        now: datetime | None = None,
    ) -> CampaignOverviewResponse | None:
        statement = select(MarketingCampaignTable).where(
            MarketingCampaignTable.id == campaign_id,
            MarketingCampaignTable.owner_id == owner_id,
            MarketingCampaignTable.project_id == project_id,
        )
        result = await self._session.execute(statement)
        campaign = result.scalar_one_or_none()
        if campaign is None:
            return None

        # Assets counts by status (only those bound to campaign_id).
        assets_stmt = (
            select(ContentAssetTable.status, func.count())
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
                ContentAssetTable.campaign_id == campaign_id,
            )
            .group_by(ContentAssetTable.status)
        )
        assets_res = await self._session.execute(assets_stmt)
        assets_by_status = {str(getattr(s, "value", s)): int(c) for s, c in assets_res.all()}

        # Jobs counts by status.
        jobs_stmt = (
            select(PublicationJobTable.status, func.count())
            .where(
                PublicationJobTable.owner_id == owner_id,
                PublicationJobTable.project_id == project_id,
                PublicationJobTable.campaign_id == campaign_id,
            )
            .group_by(PublicationJobTable.status)
        )
        jobs_res = await self._session.execute(jobs_stmt)
        jobs_by_status = {str(getattr(s, "value", s)): int(c) for s, c in jobs_res.all()}

        # jobs_skipped: number of delivery attempts with status=SKIPPED for jobs in campaign.
        skipped_stmt = (
            select(func.count())
            .select_from(PublicationDeliveryLogTable)
            .join(
                PublicationJobTable,
                PublicationJobTable.id == PublicationDeliveryLogTable.publication_job_id,
            )
            .where(
                PublicationDeliveryLogTable.owner_id == owner_id,
                PublicationDeliveryLogTable.project_id == project_id,
                PublicationJobTable.campaign_id == campaign_id,
                PublicationDeliveryLogTable.status == PublicationDeliveryLogStatus.SKIPPED,
            )
        )
        skipped_res = await self._session.execute(skipped_stmt)
        jobs_skipped = int(skipped_res.scalar_one())

        assets_total = sum(assets_by_status.values())
        jobs_total = sum(jobs_by_status.values())

        counts = CampaignOverviewCounts(
            assets_total=assets_total,
            assets_draft=assets_by_status.get(ContentAssetStatus.DRAFT.value, 0),
            assets_approved=assets_by_status.get(ContentAssetStatus.APPROVED.value, 0),
            assets_archived=assets_by_status.get(ContentAssetStatus.ARCHIVED.value, 0),
            jobs_total=jobs_total,
            jobs_scheduled=jobs_by_status.get(PublicationJobStatus.SCHEDULED.value, 0),
            jobs_queued=jobs_by_status.get(PublicationJobStatus.QUEUED.value, 0),
            jobs_running=jobs_by_status.get(PublicationJobStatus.RUNNING.value, 0),
            jobs_succeeded=jobs_by_status.get(PublicationJobStatus.SUCCEEDED.value, 0),
            jobs_failed=jobs_by_status.get(PublicationJobStatus.FAILED.value, 0),
            jobs_cancelled=jobs_by_status.get(PublicationJobStatus.CANCELLED.value, 0),
            jobs_skipped=jobs_skipped,
        )

        anchor = now or datetime.now(UTC)

        next_stmt = (
            select(func.min(PublicationJobTable.scheduled_at))
            .where(
                PublicationJobTable.owner_id == owner_id,
                PublicationJobTable.project_id == project_id,
                PublicationJobTable.campaign_id == campaign_id,
                PublicationJobTable.status == PublicationJobStatus.SCHEDULED,
                PublicationJobTable.scheduled_at.is_not(None),
                PublicationJobTable.scheduled_at > anchor,
            )
        )
        next_res = await self._session.execute(next_stmt)
        next_at = next_res.scalar_one_or_none()

        last_success_stmt = (
            select(func.max(PublicationDeliveryLogTable.created_at))
            .select_from(PublicationDeliveryLogTable)
            .join(
                PublicationJobTable,
                PublicationJobTable.id == PublicationDeliveryLogTable.publication_job_id,
            )
            .where(
                PublicationDeliveryLogTable.owner_id == owner_id,
                PublicationDeliveryLogTable.project_id == project_id,
                PublicationJobTable.campaign_id == campaign_id,
                PublicationDeliveryLogTable.status == PublicationDeliveryLogStatus.SUCCEEDED,
            )
        )
        last_res = await self._session.execute(last_success_stmt)
        last_success_at = last_res.scalar_one_or_none()

        schedule = CampaignOverviewSchedule(
            next_scheduled_publication_at=next_at,
            last_successful_publication_at=last_success_at,
        )

        recent_stmt = (
            select(PublicationJobTable)
            .where(
                PublicationJobTable.owner_id == owner_id,
                PublicationJobTable.project_id == project_id,
                PublicationJobTable.campaign_id == campaign_id,
            )
            .order_by(PublicationJobTable.created_at.desc())
            .limit(10)
        )
        recent_res = await self._session.execute(recent_stmt)
        recent_rows = list(recent_res.scalars().all())
        recent_jobs = [publication_job_to_contract(row) for row in recent_rows]

        return CampaignOverviewResponse(
            campaign=marketing_campaign_to_contract(campaign).model_dump(),
            counts=counts,
            schedule=schedule,
            recent_jobs=recent_jobs,
        )

