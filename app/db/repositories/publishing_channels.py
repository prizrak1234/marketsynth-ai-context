"""Publishing channel repository (Phase 6.0)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.publishing import PublishingChannelTable
from app.db.repositories.base import BaseRepository
from app.publishing.contracts import PublishingChannelStatus, PublishingChannelType


class PublishingChannelRepository(BaseRepository[PublishingChannelTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PublishingChannelTable)

    async def get_for_owner(
        self,
        channel_id: UUID,
        *,
        owner_id: UUID,
        project_id: UUID,
    ) -> PublishingChannelTable | None:
        statement = select(PublishingChannelTable).where(
            PublishingChannelTable.id == channel_id,
            PublishingChannelTable.owner_id == owner_id,
            PublishingChannelTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        owner_id: UUID,
        include_archived: bool = False,
        channel_type: PublishingChannelType | None = None,
        status: PublishingChannelStatus | None = None,
        limit: int = 100,
    ) -> list[PublishingChannelTable]:
        statement = (
            select(PublishingChannelTable)
            .where(
                PublishingChannelTable.project_id == project_id,
                PublishingChannelTable.owner_id == owner_id,
            )
            .order_by(PublishingChannelTable.created_at.desc())
            .limit(limit)
        )
        if not include_archived:
            statement = statement.where(
                PublishingChannelTable.status != PublishingChannelStatus.ARCHIVED,
            )
        if channel_type is not None:
            statement = statement.where(
                PublishingChannelTable.channel_type == channel_type,
            )
        if status is not None:
            statement = statement.where(PublishingChannelTable.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
