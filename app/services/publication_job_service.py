"""Publication job service — queue approved assets (Phase 6.0, no dispatch)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.models.publishing import PublicationJobTable, PublishingChannelTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.marketing.contracts import ContentAssetStatus
from app.publishing.contracts import PublicationJobStatus, PublishingChannelStatus
from app.publishing.payload_preview import build_publication_payload_preview
from app.schemas.publishing import PublicationJobCreateRequest
from app.services.transaction import transactional


class PublicationJobService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = PublicationJobRepository(session)
        self._channels = PublishingChannelRepository(session)
        self._assets = ContentAssetRepository(session)
        self._projects = ProjectRepository(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    def _assert_channel_publishable(self, channel: PublishingChannelTable) -> None:
        if channel.status != PublishingChannelStatus.ACTIVE:
            raise InvalidStateError(
                f"Publishing channel is not active (status={channel.status.value})",
            )

    def _assert_asset_publishable(self, asset: object) -> int:
        status = getattr(asset, "status", None)
        if status != ContentAssetStatus.APPROVED:
            raise InvalidStateError(
                "Only approved content assets can be queued for publication",
            )
        approved_version = getattr(asset, "approved_version_number", None)
        if approved_version is None:
            raise InvalidStateError(
                "Content asset has no approved_version_number",
            )
        return int(approved_version)

    async def create(
        self,
        owner_id: UUID,
        project_id: UUID,
        body: PublicationJobCreateRequest,
    ) -> PublicationJobTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        asset = await self._assets.get_for_project(body.asset_id, owner_id, project_id)
        if asset is None:
            return None

        channel = await self._channels.get_for_owner(
            body.channel_id,
            owner_id=owner_id,
            project_id=project_id,
        )
        if channel is None:
            return None

        approved_version = self._assert_asset_publishable(asset)
        self._assert_channel_publishable(channel)

        asset_campaign_id = getattr(asset, "campaign_id", None)
        requested_campaign_id = body.campaign_id
        if asset_campaign_id is not None:
            if requested_campaign_id is not None and requested_campaign_id != asset_campaign_id:
                raise InvalidStateError("campaign_id must match asset campaign_id")
            campaign_id = asset_campaign_id
        else:
            if requested_campaign_id is not None:
                raise InvalidStateError("campaign_id cannot be set when asset has no campaign")
            campaign_id = None

        payload_preview = build_publication_payload_preview(
            asset_id=asset.id,
            asset_version_number=approved_version,
            asset_type=asset.asset_type,
            asset_title=asset.title,
            channel_id=channel.id,
            channel_name=channel.name,
            channel_type=channel.channel_type,
        )

        status = PublicationJobStatus.QUEUED
        scheduled_at: datetime | None = None
        queued_at: datetime | None = None
        if body.scheduled_at is not None:
            # Pydantic validator already ensured aware + future UTC.
            status = PublicationJobStatus.SCHEDULED
            scheduled_at = body.scheduled_at
        else:
            queued_at = datetime.now(UTC)

        row = PublicationJobTable(
            owner_id=owner_id,
            project_id=project_id,
            asset_id=asset.id,
            asset_version_number=approved_version,
            channel_id=channel.id,
            campaign_id=campaign_id,
            status=status,
            payload_preview=payload_preview,
            error=None,
            scheduled_at=scheduled_at,
            queued_at=queued_at,
        )
        async with transactional(self._session):
            return await self._jobs.create(row)

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationJobTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._jobs.get_for_owner(
            job_id,
            owner_id=owner_id,
            project_id=project_id,
        )

    async def list(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        asset_id: UUID | None = None,
        channel_id: UUID | None = None,
        status: PublicationJobStatus | None = None,
        limit: int = 100,
    ) -> list[PublicationJobTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._jobs.list_for_project(
            project_id,
            owner_id=owner_id,
            asset_id=asset_id,
            channel_id=channel_id,
            status=status,
            limit=limit,
        )

    async def cancel(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
    ) -> PublicationJobTable | None:
        row = await self.get(owner_id, project_id, job_id)
        if row is None:
            return None
        if row.status not in (PublicationJobStatus.QUEUED, PublicationJobStatus.SCHEDULED):
            raise InvalidStateError(
                f"Publication job cannot be cancelled (status={row.status.value})",
            )
        was_scheduled = row.status == PublicationJobStatus.SCHEDULED
        row.status = PublicationJobStatus.CANCELLED
        row.finished_at = datetime.now(UTC)
        if was_scheduled:
            row.error = sanitize_text("scheduled_job_cancelled_by_user")[:512]
            row.queued_at = None
        else:
            row.error = sanitize_text("cancelled_by_user")[:512]
        async with transactional(self._session):
            return await self._jobs.update(row)

    async def reschedule(
        self,
        owner_id: UUID,
        project_id: UUID,
        job_id: UUID,
        *,
        scheduled_at: datetime,
    ) -> PublicationJobTable | None:
        row = await self.get(owner_id, project_id, job_id)
        if row is None:
            return None
        if row.status != PublicationJobStatus.SCHEDULED:
            raise InvalidStateError(
                f"Only scheduled publication jobs can be rescheduled (status={row.status.value})",
            )
        row.scheduled_at = scheduled_at
        row.queued_at = None
        async with transactional(self._session):
            return await self._jobs.update(row)
