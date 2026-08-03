"""Media asset service — placeholder containers only (Phase AI.53–AI.54)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.db.models.media import MediaAssetTable
from app.db.repositories.media_assets import MediaAssetRepository
from app.db.repositories.media_briefs import MediaBriefRepository
from app.marketing.media_brief_media_asset_conversion import (
    assert_brief_eligible_for_media_asset,
    build_placeholder_media_asset_fields,
    parse_media_type,
)
from app.marketing.media_contracts import MediaAssetStatus
from app.services.projects_service import ProjectService
from app.services.transaction import transactional


class MediaAssetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MediaAssetRepository(session)
        self._briefs = MediaBriefRepository(session)
        self._projects = ProjectService(session)

    async def _ensure_project_owned(self, owner_id: UUID, project_id: UUID) -> bool:
        project = await self._projects.get_by_id(project_id)
        return project is not None and project.owner_id == owner_id

    async def get(
        self,
        owner_id: UUID,
        project_id: UUID,
        media_asset_id: UUID,
    ) -> MediaAssetTable | None:
        return await self._repo.get_by_id_for_owner(media_asset_id, owner_id, project_id)

    async def list_by_project(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        media_brief_id: UUID | None = None,
        include_archived: bool = False,
        limit: int = 100,
    ) -> list[MediaAssetTable] | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None
        return await self._repo.list_by_project(
            owner_id,
            project_id,
            media_brief_id=media_brief_id,
            include_archived=include_archived,
            limit=limit,
        )

    async def create_placeholder_from_approved_brief(
        self,
        owner_id: UUID,
        project_id: UUID,
        brief_id: UUID,
        *,
        media_type: str,
    ) -> MediaAssetTable | None:
        if not await self._ensure_project_owned(owner_id, project_id):
            return None

        brief = await self._briefs.get_by_id_for_owner(brief_id, owner_id, project_id)
        if brief is None:
            return None

        assert_brief_eligible_for_media_asset(brief)
        parsed_type = parse_media_type(media_type)

        existing = await self._repo.get_by_brief_and_type(
            owner_id,
            project_id,
            brief_id,
            parsed_type,
        )
        if existing is not None:
            raise InvalidStateError(
                f"A media asset already exists for this brief and type ({parsed_type.value})",
            )

        fields = build_placeholder_media_asset_fields(brief, media_type=parsed_type)
        row = MediaAssetTable(
            owner_id=owner_id,
            project_id=project_id,
            media_brief_id=brief_id,
            source_media_brief_id=brief_id,
            media_type=parsed_type,
            status=MediaAssetStatus.DRAFT,
            generation_provider=fields["generation_provider"],
            generation_metadata=fields["generation_metadata"],
        )
        async with transactional(self._session):
            return await self._repo.create(row)
