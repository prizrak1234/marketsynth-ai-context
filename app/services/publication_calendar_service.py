"""Publication calendar read model (Phase 8.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.db.models.marketing import ContentAssetTable
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.models.publishing import PublicationJobTable, PublishingChannelTable
from app.db.repositories.project_repo import ProjectRepository
from app.publishing.contracts import PublicationJobStatus


class PublicationCalendarService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._projects = ProjectRepository(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def list_calendar(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        from_at: datetime | None,
        to_at: datetime | None,
        channel_id: UUID | None,
        campaign_id: UUID | None,
        status: PublicationJobStatus | None,
        limit: int = 100,
        default_statuses: tuple[PublicationJobStatus, ...] = (
            PublicationJobStatus.SCHEDULED,
            PublicationJobStatus.QUEUED,
            PublicationJobStatus.RUNNING,
        ),
    ) -> list[dict]:
        if not await self._ensure_project_owned(owner_id, project_id):
            return []

        # Normalize time bounds to UTC.
        if from_at is not None:
            from_at = from_at.astimezone(UTC)
        if to_at is not None:
            to_at = to_at.astimezone(UTC)

        statuses = [status] if status is not None else list(default_statuses)

        statement = (
            select(
                PublicationJobTable.id,
                PublicationJobTable.asset_id,
                ContentAssetTable.title,
                PublicationJobTable.channel_id,
                PublishingChannelTable.channel_type,
                PublishingChannelTable.name,
                PublicationJobTable.status,
                PublicationJobTable.scheduled_at,
                PublicationJobTable.queued_at,
                PublicationJobTable.asset_version_number,
                PublicationJobTable.campaign_id,
                MarketingCampaignTable.title,
                PublicationJobTable.created_at,
            )
            .join(
                ContentAssetTable,
                col(ContentAssetTable.id) == col(PublicationJobTable.asset_id),
            )
            .join(
                PublishingChannelTable,
                col(PublishingChannelTable.id) == col(PublicationJobTable.channel_id),
            )
            .outerjoin(
                MarketingCampaignTable,
                col(MarketingCampaignTable.id) == col(PublicationJobTable.campaign_id),
            )
            .where(
                PublicationJobTable.owner_id == owner_id,
                PublicationJobTable.project_id == project_id,
                col(PublicationJobTable.status).in_(statuses),
            )
            .order_by(
                col(PublicationJobTable.scheduled_at).is_(None),
                PublicationJobTable.scheduled_at.asc(),
                PublicationJobTable.created_at.asc(),
            )
            .limit(limit)
        )

        if channel_id is not None:
            statement = statement.where(PublicationJobTable.channel_id == channel_id)

        if campaign_id is not None:
            statement = statement.where(PublicationJobTable.campaign_id == campaign_id)

        # Use effective time for filtering:
        # scheduled_at if present else queued_at if present else created_at.
        effective_at = func.coalesce(
            col(PublicationJobTable.scheduled_at),
            col(PublicationJobTable.queued_at),
            col(PublicationJobTable.created_at),
        )
        if from_at is not None:
            statement = statement.where(effective_at >= from_at)
        if to_at is not None:
            statement = statement.where(effective_at <= to_at)

        result = await self._session.execute(statement)
        rows = result.all()
        return [
            {
                "job_id": str(job_id),
                "asset_id": str(asset_id),
                "asset_title": asset_title,
                "channel_id": str(row_channel_id),
                "channel_type": str(
                    channel_type.value if hasattr(channel_type, "value") else channel_type,
                ),
                "channel_name": channel_name,
                "status": str(job_status.value if hasattr(job_status, "value") else job_status),
                "scheduled_at": scheduled_at,
                "queued_at": queued_at,
                "asset_version_number": int(asset_version_number),
                "campaign_id": str(row_campaign_id) if row_campaign_id is not None else None,
                "campaign_title": campaign_title,
            }
            for (
                job_id,
                asset_id,
                asset_title,
                row_channel_id,
                channel_type,
                channel_name,
                job_status,
                scheduled_at,
                queued_at,
                asset_version_number,
                row_campaign_id,
                campaign_title,
                _created_at,
            ) in rows
        ]

