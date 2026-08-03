"""Publication package persistence (Phase AI.43)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import PublicationPackageTable
from app.marketing.contracts import PublicationPackageChannel, PublicationPackageStatus


class PublicationPackageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, row: PublicationPackageTable) -> PublicationPackageTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, row: PublicationPackageTable) -> PublicationPackageTable:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id_for_owner(
        self,
        package_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> PublicationPackageTable | None:
        statement = select(PublicationPackageTable).where(
            PublicationPackageTable.id == package_id,
            PublicationPackageTable.owner_id == owner_id,
            PublicationPackageTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_asset_and_channel(
        self,
        owner_id: UUID,
        project_id: UUID,
        content_asset_id: UUID,
        channel: PublicationPackageChannel,
    ) -> PublicationPackageTable | None:
        statement = select(PublicationPackageTable).where(
            PublicationPackageTable.owner_id == owner_id,
            PublicationPackageTable.project_id == project_id,
            PublicationPackageTable.content_asset_id == content_asset_id,
            PublicationPackageTable.channel == channel,
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
    ) -> list[PublicationPackageTable]:
        statement = select(PublicationPackageTable).where(
            PublicationPackageTable.owner_id == owner_id,
            PublicationPackageTable.project_id == project_id,
        )
        if content_asset_id is not None:
            statement = statement.where(
                PublicationPackageTable.content_asset_id == content_asset_id,
            )
        if not include_archived:
            statement = statement.where(
                PublicationPackageTable.status != PublicationPackageStatus.ARCHIVED,
            )
        statement = (
            statement.order_by(PublicationPackageTable.updated_at.desc()).limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
