"""Publication delivery log repository (Phase 6.1)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.publication_delivery_log import PublicationDeliveryLogTable
from app.db.repositories.base import BaseRepository
from app.publishing.contracts import PublicationDeliveryLogStatus


class PublicationDeliveryLogRepository(BaseRepository[PublicationDeliveryLogTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PublicationDeliveryLogTable)

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        publication_job_id: UUID | None = None,
        channel_id: UUID | None = None,
        status: PublicationDeliveryLogStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PublicationDeliveryLogTable]:
        statement = select(PublicationDeliveryLogTable).where(
            PublicationDeliveryLogTable.project_id == project_id,
            PublicationDeliveryLogTable.owner_id == owner_id,
        )
        if publication_job_id is not None:
            statement = statement.where(
                PublicationDeliveryLogTable.publication_job_id == publication_job_id,
            )
        if channel_id is not None:
            statement = statement.where(
                PublicationDeliveryLogTable.channel_id == channel_id,
            )
        if status is not None:
            statement = statement.where(PublicationDeliveryLogTable.status == status)
        statement = (
            statement.order_by(PublicationDeliveryLogTable.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_by_status(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> dict[str, int]:
        statement = (
            select(PublicationDeliveryLogTable.status, func.count())
            .where(
                PublicationDeliveryLogTable.owner_id == owner_id,
                PublicationDeliveryLogTable.created_at >= since,
            )
            .group_by(PublicationDeliveryLogTable.status)
        )
        if project_id is not None:
            statement = statement.where(
                PublicationDeliveryLogTable.project_id == project_id,
            )
        result = await self.session.execute(statement)
        counts = {status.value: 0 for status in PublicationDeliveryLogStatus}
        for status, count in result.all():
            key = status.value if hasattr(status, "value") else str(status)
            counts[key] = int(count)
        return counts

    async def duration_stats(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> tuple[float | None, int | None]:
        statement = select(
            func.avg(PublicationDeliveryLogTable.duration_ms),
            func.max(PublicationDeliveryLogTable.duration_ms),
        ).where(
            PublicationDeliveryLogTable.owner_id == owner_id,
            PublicationDeliveryLogTable.created_at >= since,
            PublicationDeliveryLogTable.duration_ms.is_not(None),
        )
        if project_id is not None:
            statement = statement.where(
                PublicationDeliveryLogTable.project_id == project_id,
            )
        result = await self.session.execute(statement)
        avg_ms, max_ms = result.one()
        avg_value = round(float(avg_ms), 2) if avg_ms is not None else None
        max_value = int(max_ms) if max_ms is not None else None
        return avg_value, max_value

    async def failed_counts_by_channel(
        self,
        *,
        owner_id: UUID,
        project_id: UUID | None,
        since: datetime,
    ) -> dict[str, int]:
        statement = (
            select(PublicationDeliveryLogTable.channel_id, func.count())
            .where(
                PublicationDeliveryLogTable.owner_id == owner_id,
                PublicationDeliveryLogTable.created_at >= since,
                PublicationDeliveryLogTable.status == PublicationDeliveryLogStatus.FAILED,
            )
            .group_by(PublicationDeliveryLogTable.channel_id)
        )
        if project_id is not None:
            statement = statement.where(
                PublicationDeliveryLogTable.project_id == project_id,
            )
        result = await self.session.execute(statement)
        return {str(channel_id): int(count) for channel_id, count in result.all()}
