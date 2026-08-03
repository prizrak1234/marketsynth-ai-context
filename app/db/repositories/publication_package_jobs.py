"""Publication package job persistence (Phase AI.62)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.publication_package_job import PublicationPackageJobTable
from app.publishing_foundation.contracts import (
    PublicationPackageJobScheduleStatus,
    PublicationPackageJobStatus,
)

_ACTIVE_STATUSES = (
    PublicationPackageJobStatus.QUEUED,
    PublicationPackageJobStatus.RUNNING,
)


class PublicationPackageJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, row: PublicationPackageJobTable) -> PublicationPackageJobTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, row: PublicationPackageJobTable) -> PublicationPackageJobTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        job_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> PublicationPackageJobTable | None:
        statement = select(PublicationPackageJobTable).where(
            PublicationPackageJobTable.id == job_id,
            PublicationPackageJobTable.owner_id == owner_id,
            PublicationPackageJobTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        publication_package_id: UUID | None = None,
        limit: int = 100,
    ) -> list[PublicationPackageJobTable]:
        statement = select(PublicationPackageJobTable).where(
            PublicationPackageJobTable.owner_id == owner_id,
            PublicationPackageJobTable.project_id == project_id,
        )
        if publication_package_id is not None:
            statement = statement.where(
                PublicationPackageJobTable.publication_package_id == publication_package_id,
            )
        statement = (
            statement.order_by(PublicationPackageJobTable.created_at.desc()).limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active_for_package_channel(
        self,
        owner_id: UUID,
        project_id: UUID,
        package_id: UUID,
        channel_id: UUID,
    ) -> PublicationPackageJobTable | None:
        statement = select(PublicationPackageJobTable).where(
            PublicationPackageJobTable.owner_id == owner_id,
            PublicationPackageJobTable.project_id == project_id,
            PublicationPackageJobTable.publication_package_id == package_id,
            PublicationPackageJobTable.channel_id == channel_id,
            PublicationPackageJobTable.status.in_(_ACTIVE_STATUSES),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key_hash(
        self,
        owner_id: UUID,
        project_id: UUID,
        idempotency_key_hash: str,
    ) -> PublicationPackageJobTable | None:
        statement = select(PublicationPackageJobTable).where(
            PublicationPackageJobTable.owner_id == owner_id,
            PublicationPackageJobTable.project_id == project_id,
            PublicationPackageJobTable.idempotency_key_hash == idempotency_key_hash,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_due_for_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> list[PublicationPackageJobTable]:
        anchor = (now or datetime.now(UTC)).astimezone(UTC)
        statement = (
            select(PublicationPackageJobTable)
            .where(
                PublicationPackageJobTable.owner_id == owner_id,
                PublicationPackageJobTable.project_id == project_id,
                PublicationPackageJobTable.status == PublicationPackageJobStatus.QUEUED,
                PublicationPackageJobTable.schedule_status.in_(
                    (
                        PublicationPackageJobScheduleStatus.SCHEDULED,
                        PublicationPackageJobScheduleStatus.DUE,
                    ),
                ),
                PublicationPackageJobTable.scheduled_for.is_not(None),
                PublicationPackageJobTable.scheduled_for <= anchor,
            )
            .order_by(PublicationPackageJobTable.scheduled_for.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
