"""Media asset persistence (Phase AI.53)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.media import MediaAssetTable
from app.marketing.media_contracts import MediaAssetStatus, MediaAssetType


class MediaAssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, row: MediaAssetTable) -> MediaAssetTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, row: MediaAssetTable) -> MediaAssetTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> MediaAssetTable | None:
        statement = select(MediaAssetTable).where(
            MediaAssetTable.id == asset_id,
            MediaAssetTable.owner_id == owner_id,
            MediaAssetTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_brief_and_type(
        self,
        owner_id: UUID,
        project_id: UUID,
        media_brief_id: UUID,
        media_type: MediaAssetType,
    ) -> MediaAssetTable | None:
        statement = select(MediaAssetTable).where(
            MediaAssetTable.owner_id == owner_id,
            MediaAssetTable.project_id == project_id,
            MediaAssetTable.media_brief_id == media_brief_id,
            MediaAssetTable.media_type == media_type,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        media_brief_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[MediaAssetTable]:
        statement = select(MediaAssetTable).where(
            MediaAssetTable.owner_id == owner_id,
            MediaAssetTable.project_id == project_id,
        )
        if media_brief_id is not None:
            statement = statement.where(MediaAssetTable.media_brief_id == media_brief_id)
        if not include_archived:
            statement = statement.where(MediaAssetTable.status != MediaAssetStatus.ARCHIVED)
        statement = statement.order_by(MediaAssetTable.updated_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
