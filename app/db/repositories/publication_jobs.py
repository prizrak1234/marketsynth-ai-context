"""Publication job repository (Phase 6.0)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select, update

from app.db.base import utc_now
from app.db.models.publishing import PublicationJobTable
from app.db.repositories.base import BaseRepository
from app.publishing.contracts import PublicationJobStatus


class PublicationJobRepository(BaseRepository[PublicationJobTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PublicationJobTable)

    async def get_for_owner(
        self,
        job_id: UUID,
        *,
        owner_id: UUID,
        project_id: UUID,
    ) -> PublicationJobTable | None:
        statement = select(PublicationJobTable).where(
            PublicationJobTable.id == job_id,
            PublicationJobTable.owner_id == owner_id,
            PublicationJobTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        asset_id: UUID | None = None,
        channel_id: UUID | None = None,
        status: PublicationJobStatus | None = None,
        limit: int = 100,
    ) -> list[PublicationJobTable]:
        statement = (
            select(PublicationJobTable)
            .where(
                PublicationJobTable.project_id == project_id,
                PublicationJobTable.owner_id == owner_id,
            )
            .order_by(PublicationJobTable.created_at.desc())
            .limit(limit)
        )
        if asset_id is not None:
            statement = statement.where(PublicationJobTable.asset_id == asset_id)
        if channel_id is not None:
            statement = statement.where(PublicationJobTable.channel_id == channel_id)
        if status is not None:
            statement = statement.where(PublicationJobTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_campaign(
        self,
        *,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        limit: int = 100,
    ) -> list[PublicationJobTable]:
        statement = (
            select(PublicationJobTable)
            .where(
                PublicationJobTable.owner_id == owner_id,
                PublicationJobTable.project_id == project_id,
                PublicationJobTable.campaign_id == campaign_id,
            )
            .order_by(PublicationJobTable.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_queued(
        self,
        *,
        limit: int = 50,
        project_id: UUID | None = None,
        owner_id: UUID | None = None,
    ) -> list[PublicationJobTable]:
        statement = (
            select(PublicationJobTable)
            .where(PublicationJobTable.status == PublicationJobStatus.QUEUED)
            .order_by(PublicationJobTable.created_at.asc())
            .limit(limit)
        )
        if project_id is not None:
            statement = statement.where(PublicationJobTable.project_id == project_id)
        if owner_id is not None:
            statement = statement.where(PublicationJobTable.owner_id == owner_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def claim_queued_job(self, job_id: UUID) -> PublicationJobTable | None:
        """Atomically transition queued → running."""
        now = utc_now()
        statement = (
            update(PublicationJobTable)
            .where(
                PublicationJobTable.id == job_id,
                PublicationJobTable.status == PublicationJobStatus.QUEUED,
            )
            .values(
                status=PublicationJobStatus.RUNNING,
                started_at=now,
            )
            .returning(PublicationJobTable)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_succeeded(self, row: PublicationJobTable) -> PublicationJobTable:
        row.status = PublicationJobStatus.SUCCEEDED
        row.error = None
        row.finished_at = utc_now()
        return await self.update(row)

    async def mark_failed(
        self,
        row: PublicationJobTable,
        *,
        error: str,
    ) -> PublicationJobTable:
        row.status = PublicationJobStatus.FAILED
        row.error = error[:512]
        row.finished_at = utc_now()
        return await self.update(row)

    async def requeue_after_failure(
        self,
        row: PublicationJobTable,
        *,
        error: str,
    ) -> PublicationJobTable:
        row.attempts += 1
        row.status = PublicationJobStatus.QUEUED
        row.started_at = None
        row.error = error[:512]
        return await self.update(row)

    async def reset_for_replay(self, row: PublicationJobTable) -> PublicationJobTable:
        row.status = PublicationJobStatus.QUEUED
        row.attempts = 0
        row.error = None
        row.started_at = None
        row.finished_at = None
        return await self.update(row)

    async def list_for_batch_replay(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        statuses: list[PublicationJobStatus],
        channel_id: UUID | None = None,
        limit: int = 50,
    ) -> list[PublicationJobTable]:
        statement = (
            select(PublicationJobTable)
            .where(
                PublicationJobTable.project_id == project_id,
                PublicationJobTable.owner_id == owner_id,
                col(PublicationJobTable.status).in_(statuses),
            )
            .order_by(PublicationJobTable.created_at.asc())
            .limit(limit)
        )
        if channel_id is not None:
            statement = statement.where(PublicationJobTable.channel_id == channel_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_by_status(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime | None = None,
    ) -> dict[str, int]:
        statement = (
            select(PublicationJobTable.status, func.count())
            .where(PublicationJobTable.owner_id == owner_id)
            .group_by(PublicationJobTable.status)
        )
        if project_id is not None:
            statement = statement.where(PublicationJobTable.project_id == project_id)
        if since is not None:
            statement = statement.where(PublicationJobTable.created_at >= since)
        result = await self.session.execute(statement)
        counts = {status.value: 0 for status in PublicationJobStatus}
        for status, count in result.all():
            key = status.value if hasattr(status, "value") else str(status)
            counts[key] = int(count)
        return counts

    async def count_failed_jobs(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> int:
        statement = select(func.count()).where(
            PublicationJobTable.owner_id == owner_id,
            PublicationJobTable.status == PublicationJobStatus.FAILED,
        )
        if project_id is not None:
            statement = statement.where(PublicationJobTable.project_id == project_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def oldest_queued_job_age_seconds(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> int | None:
        statement = (
            select(PublicationJobTable.created_at)
            .where(
                PublicationJobTable.owner_id == owner_id,
                PublicationJobTable.status == PublicationJobStatus.QUEUED,
            )
            .order_by(PublicationJobTable.created_at.asc())
            .limit(1)
        )
        if project_id is not None:
            statement = statement.where(PublicationJobTable.project_id == project_id)
        result = await self.session.execute(statement)
        created_at = result.scalar_one_or_none()
        if created_at is None:
            return None
        anchor = created_at
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=UTC)
        return max(0, int((utc_now() - anchor).total_seconds()))

    async def count_pending_global(self) -> int:
        statement = select(func.count()).where(
            PublicationJobTable.status == PublicationJobStatus.QUEUED,
        )
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def count_scheduled_jobs(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
    ) -> int:
        statement = select(func.count()).where(
            PublicationJobTable.owner_id == owner_id,
            PublicationJobTable.status == PublicationJobStatus.SCHEDULED,
        )
        if project_id is not None:
            statement = statement.where(PublicationJobTable.project_id == project_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def count_due_scheduled_jobs(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        now: datetime | None = None,
    ) -> int:
        anchor = now or utc_now()
        statement = select(func.count()).where(
            PublicationJobTable.owner_id == owner_id,
            PublicationJobTable.status == PublicationJobStatus.SCHEDULED,
            PublicationJobTable.scheduled_at.is_not(None),
            PublicationJobTable.scheduled_at <= anchor,
        )
        if project_id is not None:
            statement = statement.where(PublicationJobTable.project_id == project_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def next_scheduled_publication_at(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        now: datetime | None = None,
    ) -> datetime | None:
        anchor = now or utc_now()
        statement = (
            select(PublicationJobTable.scheduled_at)
            .where(
                PublicationJobTable.owner_id == owner_id,
                PublicationJobTable.status == PublicationJobStatus.SCHEDULED,
                PublicationJobTable.scheduled_at.is_not(None),
                PublicationJobTable.scheduled_at > anchor,
            )
            .order_by(PublicationJobTable.scheduled_at.asc())
            .limit(1)
        )
        if project_id is not None:
            statement = statement.where(PublicationJobTable.project_id == project_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def count_cancelled_scheduled_jobs(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> int:
        statement = select(func.count()).where(
            PublicationJobTable.owner_id == owner_id,
            PublicationJobTable.status == PublicationJobStatus.CANCELLED,
            PublicationJobTable.scheduled_at.is_not(None),
            PublicationJobTable.finished_at.is_not(None),
            PublicationJobTable.finished_at >= since,
        )
        if project_id is not None:
            statement = statement.where(PublicationJobTable.project_id == project_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())
