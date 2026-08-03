"""Human review queue read model (Phase 14.0)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.content_assets import ContentAssetRepository
from app.schemas.contracts import ReviewQueueItemType
from app.schemas.review_queue import ReviewQueueItem, ReviewQueueResponse
from app.services.projects_service import ProjectService


class ReviewQueueService:
    """Read-only aggregation of objects awaiting human approval."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._assets = ContentAssetRepository(session)
        self._projects = ProjectService(session)

    async def get_queue(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        limit: int = 500,
    ) -> ReviewQueueResponse | None:
        listed = await self.list_for_tool(owner_id, project_id, limit=limit)
        if listed is None:
            return None
        items, _total = listed
        return ReviewQueueResponse(items=items)

    async def list_for_tool(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        limit: int,
    ) -> tuple[list[ReviewQueueItem], int] | None:
        project = await self._projects.get_by_id(project_id)
        if project is None or project.owner_id != owner_id:
            return None

        total_count = await self._assets.count_pending_human_review(owner_id, project_id)
        rows = await self._assets.list_pending_human_review(
            owner_id,
            project_id,
            limit=limit,
        )
        items = [
            ReviewQueueItem(
                type=ReviewQueueItemType.CONTENT_ASSET,
                id=asset.id,
                campaign_id=asset.campaign_id,
                campaign_title=campaign_title,
                title=asset.title,
                status=asset.status,
                current_version_number=asset.current_version_number,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
            for asset, campaign_title in rows
        ]
        return items, total_count

    async def count_pending_assets(
        self,
        owner_id: UUID,
        project_id: UUID,
        *,
        campaign_id: UUID | None = None,
    ) -> int:
        return await self._assets.count_pending_human_review(
            owner_id,
            project_id,
            campaign_id=campaign_id,
        )
