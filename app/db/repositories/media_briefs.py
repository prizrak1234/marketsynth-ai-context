"""Media brief persistence (Phase AI.50)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.media import MediaBriefTable


class MediaBriefRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, row: MediaBriefTable) -> MediaBriefTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, row: MediaBriefTable) -> MediaBriefTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        brief_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MediaBriefTable | None:
        statement = select(MediaBriefTable).where(
            MediaBriefTable.id == brief_id,
            MediaBriefTable.owner_id == owner_id,
            MediaBriefTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_content_asset_id(
        self,
        owner_id: UUID,
        project_id: UUID,
        content_asset_id: UUID,
    ) -> MediaBriefTable | None:
        statement = select(MediaBriefTable).where(
            MediaBriefTable.owner_id == owner_id,
            MediaBriefTable.project_id == project_id,
            MediaBriefTable.content_asset_id == content_asset_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        content_asset_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[MediaBriefTable]:
        statement = select(MediaBriefTable).where(
            MediaBriefTable.owner_id == owner_id,
            MediaBriefTable.project_id == project_id,
        )
        if content_asset_id is not None:
            statement = statement.where(MediaBriefTable.content_asset_id == content_asset_id)
        if not include_archived:
            from app.marketing.media_contracts import MediaBriefStatus

            statement = statement.where(MediaBriefTable.status != MediaBriefStatus.ARCHIVED)
        statement = statement.order_by(MediaBriefTable.updated_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
