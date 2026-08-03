"""Content asset version repository (Phase 4.4)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing import ContentAssetVersionTable
from app.db.repositories.base import BaseRepository


class ContentAssetVersionRepository(BaseRepository[ContentAssetVersionTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ContentAssetVersionTable)

    async def create_version(self, row: ContentAssetVersionTable) -> ContentAssetVersionTable:
        return await self.create(row)

    async def get_version(
        self,
        asset_id: UUID,
        version_number: int,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentAssetVersionTable | None:
        statement = select(ContentAssetVersionTable).where(
            ContentAssetVersionTable.asset_id == asset_id,
            ContentAssetVersionTable.version_number == version_number,
            ContentAssetVersionTable.owner_id == owner_id,
            ContentAssetVersionTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> list[ContentAssetVersionTable]:
        statement = (
            select(ContentAssetVersionTable)
            .where(
                ContentAssetVersionTable.asset_id == asset_id,
                ContentAssetVersionTable.owner_id == owner_id,
                ContentAssetVersionTable.project_id == project_id,
            )
            .order_by(ContentAssetVersionTable.version_number.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_version(
        self,
        asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentAssetVersionTable | None:
        statement = (
            select(ContentAssetVersionTable)
            .where(
                ContentAssetVersionTable.asset_id == asset_id,
                ContentAssetVersionTable.owner_id == owner_id,
                ContentAssetVersionTable.project_id == project_id,
            )
            .order_by(ContentAssetVersionTable.version_number.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
