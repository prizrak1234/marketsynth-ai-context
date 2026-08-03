"""Content asset repository (Phase 4.0)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.marketing import ContentAssetTable
from app.db.models.marketing_campaigns import MarketingCampaignTable
from app.db.repositories.base import BaseRepository
from app.db.repositories.enum_filters import enum_column_not_equals
from app.marketing.contracts import ContentAssetStatus, ContentAssetType


def _exclude_archived_status():
    """Exclude archived assets across PostgreSQL/SQLite enum storage."""
    return enum_column_not_equals(ContentAssetTable.status, ContentAssetStatus.ARCHIVED)


class ContentAssetRepository(BaseRepository[ContentAssetTable]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ContentAssetTable)

    async def get_by_id_for_owner(
        self,
        asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentAssetTable | None:
        return await self.get_for_project(asset_id, owner_id, project_id)

    async def get_by_source_specialist_output_id(
        self,
        owner_id: UUID,
        project_id: UUID,
        specialist_output_id: UUID,
    ) -> ContentAssetTable | None:
        statement = (
            select(ContentAssetTable)
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
                ContentAssetTable.source_specialist_output_id == specialist_output_id,
                _exclude_archived_status(),
            )
            .order_by(ContentAssetTable.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_source_specialist_output_id(
        self,
        owner_id: UUID,
        project_id: UUID,
        specialist_output_id: UUID,
    ) -> list[ContentAssetTable]:
        statement = (
            select(ContentAssetTable)
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
                ContentAssetTable.source_specialist_output_id == specialist_output_id,
                _exclude_archived_status(),
            )
            .order_by(ContentAssetTable.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_for_project(
        self,
        asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> ContentAssetTable | None:
        statement = select(ContentAssetTable).where(
            ContentAssetTable.id == asset_id,
            ContentAssetTable.owner_id == owner_id,
            ContentAssetTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        row: ContentAssetTable,
        status: ContentAssetStatus,
    ) -> ContentAssetTable:
        row.status = status
        return await self.update(row)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        include_archived: bool = False,
        status: ContentAssetStatus | None = None,
        asset_type: ContentAssetType | None = None,
        limit: int = 100,
    ) -> list[ContentAssetTable]:
        statement = (
            select(ContentAssetTable)
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
            )
            .order_by(ContentAssetTable.created_at.desc())
            .limit(limit)
        )
        if not include_archived:
            statement = statement.where(
                _exclude_archived_status(),
            )
        if status is not None:
            statement = statement.where(ContentAssetTable.status == status)
        if asset_type is not None:
            statement = statement.where(ContentAssetTable.asset_type == asset_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
        *,
        include_archived: bool = False,
        status: ContentAssetStatus | None = None,
        asset_type: ContentAssetType | None = None,
        limit: int = 100,
    ) -> list[ContentAssetTable]:
        statement = (
            select(ContentAssetTable)
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
                ContentAssetTable.brief_id == brief_id,
            )
            .order_by(ContentAssetTable.created_at.desc())
            .limit(limit)
        )
        if not include_archived:
            statement = statement.where(
                _exclude_archived_status(),
            )
        if status is not None:
            statement = statement.where(ContentAssetTable.status == status)
        if asset_type is not None:
            statement = statement.where(ContentAssetTable.asset_type == asset_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_campaign(
        self,
        owner_id: UUID,
        project_id: UUID,
        campaign_id: UUID,
        *,
        include_archived: bool = False,
        status: ContentAssetStatus | None = None,
        asset_type: ContentAssetType | None = None,
        limit: int = 100,
    ) -> list[ContentAssetTable]:
        statement = (
            select(ContentAssetTable)
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
                ContentAssetTable.campaign_id == campaign_id,
            )
            .order_by(ContentAssetTable.created_at.desc())
            .limit(limit)
        )
        if not include_archived:
            statement = statement.where(
                _exclude_archived_status(),
            )
        if status is not None:
            statement = statement.where(ContentAssetTable.status == status)
        if asset_type is not None:
            statement = statement.where(ContentAssetTable.asset_type == asset_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def archive(self, row: ContentAssetTable) -> ContentAssetTable:
        row.status = ContentAssetStatus.ARCHIVED
        return await self.update(row)

    @staticmethod
    def _pending_human_review_filter():
        return (ContentAssetTable.status == ContentAssetStatus.REVIEW,)

    async def count_pending_human_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        campaign_id: UUID | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(ContentAssetTable)
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
                *self._pending_human_review_filter(),
            )
        )
        if campaign_id is not None:
            statement = statement.where(ContentAssetTable.campaign_id == campaign_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def list_pending_human_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        limit: int = 500,
    ) -> list[tuple[ContentAssetTable, str | None]]:
        statement = (
            select(ContentAssetTable, MarketingCampaignTable.title)
            .outerjoin(
                MarketingCampaignTable,
                ContentAssetTable.campaign_id == MarketingCampaignTable.id,
            )
            .where(
                ContentAssetTable.owner_id == owner_id,
                ContentAssetTable.project_id == project_id,
                *self._pending_human_review_filter(),
            )
            .order_by(ContentAssetTable.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [(asset, campaign_title) for asset, campaign_title in result.all()]

    async def max_revision_number_for_source(
        self,
        source_asset_id: UUID,
        owner_id: UUID,
        project_id: UUID,
    ) -> int:
        statement = select(func.max(ContentAssetTable.revision_number)).where(
            ContentAssetTable.source_asset_id == source_asset_id,
            ContentAssetTable.owner_id == owner_id,
            ContentAssetTable.project_id == project_id,
        )
        result = await self.session.execute(statement)
        value = result.scalar_one_or_none()
        if value is None:
            return 0
        return int(value)
