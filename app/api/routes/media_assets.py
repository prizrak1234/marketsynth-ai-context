"""Media assets API — placeholder containers only (Phase AI.53)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import media_asset_to_contract
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.marketing.media_contracts import MediaAsset
from app.services.media_asset_service import MediaAssetService

router = APIRouter(
    prefix="/projects/{project_id}/media-assets",
    tags=["media-assets"],
)


@router.get("", response_model=list[MediaAsset])
async def list_media_assets(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    media_brief_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MediaAsset]:
    service = MediaAssetService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        media_brief_id=media_brief_id,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [media_asset_to_contract(row) for row in rows]


@router.get("/{media_asset_id}", response_model=MediaAsset)
async def get_media_asset(
    media_asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaAsset:
    service = MediaAssetService(session)
    row = await service.get(current_user.id, project.id, media_asset_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    return media_asset_to_contract(row)
