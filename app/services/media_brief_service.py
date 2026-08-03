"""Media brief service — brief layer only, no generation (Phase AI.50–AI.52)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.models.media import MediaBriefTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.marketing.content_asset_media_brief_conversion import (
    assert_asset_eligible_for_media_brief,
    build_media_brief_fields_from_asset,
)
from app.marketing.media_brief_policy import (
    assert_media_brief_can_be_approved,
    assert_media_brief_can_be_archived,
    assert_media_brief_can_submit_for_review,
    validate_media_brief_transition,
)
from app.marketing.media_contracts import MediaBriefStatus
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class MediaBriefService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MediaBriefRepository(session)
        self._assets = ContentAssetRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> MediaBriefTable | None:
        return await self._repo.get_by_id_for_owner(brief_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        content_asset_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[MediaBriefTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._repo.list_by_project(
            owner_id,
            project_id,
            content_asset_id=content_asset_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def create_from_approved_content_asset(
        self,
        owner_id: UUID,
        project_id: UUID,
        content_asset_id: UUID,
        *,
        title: str | None = None,
        goal: str | None = None,
        target_audience: str | None = None,
        platform: str | None = None,
        creative_direction: str | None = None,
        visual_style: str | None = None,
        composition: str | None = None,
        text_overlay: str | None = None,
        references: list[Any] | None = None,
    ) -> MediaBriefTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        asset = await self._assets.get_by_id_for_owner(content_asset_id, owner_id, project_id)
        if asset is None:
            return None

        assert_asset_eligible_for_media_brief(asset)

        existing = await self._repo.get_by_content_asset_id(
            owner_id,
            project_id,
            content_asset_id,
        )
        if existing is not None:
            raise InvalidStateError(
                "A media brief already exists for this content asset",
            )

        fields = build_media_brief_fields_from_asset(
            asset,
            title=title,
            goal=goal,
            target_audience=target_audience,
            platform=platform,
            creative_direction=creative_direction,
            visual_style=visual_style,
            composition=composition,
            text_overlay=text_overlay,
            references=references,
        )

        row = MediaBriefTable(
            owner_id=owner_id,
            project_id=project_id,
            content_asset_id=content_asset_id,
            source_content_asset_id=content_asset_id,
            status=MediaBriefStatus.DRAFT,
            title=fields["title"],
            goal=fields["goal"],
            target_audience=fields["target_audience"],
            platform=fields["platform"],
            creative_direction=fields["creative_direction"],
            visual_style=fields["visual_style"],
            composition=fields["composition"],
            text_overlay=fields["text_overlay"],
            references=fields["references"],
        )
        async with transactional(self._session):
            return await self._repo.create(row)

    async def submit_for_review(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> MediaBriefTable | None:
        row = await self.get(owner_id, project_id, brief_id)
        if row is None:
            return None

        assert_media_brief_can_submit_for_review(row)
        validate_media_brief_transition(row.status, MediaBriefStatus.REVIEW)
        row.status = MediaBriefStatus.REVIEW
        row.submitted_for_review_at = datetime.now(UTC)

        async with transactional(self._session):
            return await self._repo.update(row)

    async def approve_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> MediaBriefTable | None:
        row = await self.get(owner_id, project_id, brief_id)
        if row is None:
            return None

        assert_media_brief_can_be_approved(row)
        validate_media_brief_transition(row.status, MediaBriefStatus.APPROVED)
        row.status = MediaBriefStatus.APPROVED
        row.approved_at = datetime.now(UTC)

        async with transactional(self._session):
            return await self._repo.update(row)

    async def archive_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
    ) -> MediaBriefTable | None:
        row = await self.get(owner_id, project_id, brief_id)
        if row is None:
            return None

        assert_media_brief_can_be_archived(row)
        validate_media_brief_transition(row.status, MediaBriefStatus.ARCHIVED)
        row.status = MediaBriefStatus.ARCHIVED

        async with transactional(self._session):
            return await self._repo.update(row)
