"""Publication scheduler — release scheduled jobs into the queue (Phase 8.0)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.exceptions import InvalidStateError
from app.db.models.publishing import PublicationJobTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.db.repositories.publishing_channels import PublishingChannelRepository
from app.marketing.contracts import ContentAssetStatus
from app.publishing.contracts import PublicationJobStatus, PublishingChannelStatus
from app.services.transaction import transactional


class PublicationSchedulerService:
    """Release due scheduled publication jobs into the queued state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._jobs = PublicationJobRepository(session)
        self._assets = ContentAssetRepository(session)
        self._channels = PublishingChannelRepository(session)
        self._projects = ProjectRepository(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def _release_one(self, row: PublicationJobTable, *, now: datetime) -> bool:
        if row.status != PublicationJobStatus.SCHEDULED:
            return False
        if row.scheduled_at is None:
            # Corrupt row: fail fast so it does not get stuck forever.
            async with transactional(self._session):
                row.status = PublicationJobStatus.FAILED
                row.error = "scheduled_job_missing_scheduled_at"
                await self._jobs.update(row)
            return False

        anchor = row.scheduled_at
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=UTC)
        if anchor > now:
            return False

        asset = await self._assets.get_for_project(row.asset_id, row.owner_id, row.project_id)
        channel = await self._channels.get_for_owner(
            row.channel_id,
            owner_id=row.owner_id,
            project_id=row.project_id,
        )
        # If project was deleted or transferred, treat as ownership loss.
        if not await self._ensure_project_owned(row.owner_id, row.project_id):
            async with transactional(self._session):
                row.status = PublicationJobStatus.FAILED
                row.error = "project_not_owned_for_scheduled_job"
                await self._jobs.update(row)
            return False

        if asset is None or channel is None:
            async with transactional(self._session):
                row.status = PublicationJobStatus.FAILED
                row.error = "scheduled_job_missing_asset_or_channel"
                await self._jobs.update(row)
            return False

        if channel.status != PublishingChannelStatus.ACTIVE:
            async with transactional(self._session):
                row.status = PublicationJobStatus.FAILED
                row.error = "scheduled_job_channel_not_active"
                await self._jobs.update(row)
            return False

        if asset.status != ContentAssetStatus.APPROVED:
            async with transactional(self._session):
                row.status = PublicationJobStatus.FAILED
                row.error = "scheduled_job_asset_not_approved"
                await self._jobs.update(row)
            return False

        if asset.approved_version_number is None:
            async with transactional(self._session):
                row.status = PublicationJobStatus.FAILED
                row.error = "scheduled_job_missing_approved_version_number"
                await self._jobs.update(row)
            return False

        if int(asset.approved_version_number) != row.asset_version_number:
            async with transactional(self._session):
                row.status = PublicationJobStatus.FAILED
                row.error = "scheduled_job_version_mismatch"
                await self._jobs.update(row)
            return False

        async with transactional(self._session):
            row.status = PublicationJobStatus.QUEUED
            row.queued_at = now
            await self._jobs.update(row)
        return True

    async def release_due_jobs(self, *, now: datetime | None = None, limit: int = 100) -> int:
        """Release due scheduled jobs into QUEUED.

        - Only jobs with status=SCHEDULED and scheduled_at <= now are considered.
        - Jobs with invalid asset/channel or invariant violations fail closed.
        """
        now = now or datetime.now(UTC)
        statement = (
            select(PublicationJobTable)
            .where(
                PublicationJobTable.status == PublicationJobStatus.SCHEDULED,
                col(PublicationJobTable.scheduled_at).is_not(None),
                PublicationJobTable.scheduled_at <= now,
            )
            .order_by(PublicationJobTable.scheduled_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        rows = list(result.scalars().all())
        released = 0
        for row in rows:
            try:
                if await self._release_one(row, now=now):
                    released += 1
            except InvalidStateError:
                # Defensive: treat invalid rows as failed to avoid infinite scheduling loops.
                async with transactional(self._session):
                    row.status = PublicationJobStatus.FAILED
                    row.error = "scheduled_job_invalid_state"
                    await self._jobs.update(row)
        return released

