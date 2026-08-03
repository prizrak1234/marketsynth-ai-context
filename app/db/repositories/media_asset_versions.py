"""Media asset version persistence (Phase AI.58)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.media import MediaAssetVersionTable


class MediaAssetVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, row: MediaAssetVersionTable) -> MediaAssetVersionTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def list_versions(
        self,
        media_asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[MediaAssetVersionTable]:
        statement = (
            select(MediaAssetVersionTable)
            .where(
                MediaAssetVersionTable.media_asset_id == media_asset_id,
                MediaAssetVersionTable.owner_id == owner_id,
                MediaAssetVersionTable.project_id == project_id,
            )
            .order_by(MediaAssetVersionTable.version_number.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
