"""Media briefs API — visual task layer, no generation (Phase AI.50–AI.52)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import media_brief_to_contract, media_generation_job_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.marketing.media_contracts import MediaBrief
from app.media_generation.contracts import MediaGenerationJob
from app.schemas.contracts import CreateMediaAssetFromBriefResponse
from app.schemas.marketing import CreateMediaAssetRequest
from app.schemas.media_generation import CreateMediaGenerationJobBody
from app.services.media_asset_service import MediaAssetService
from app.services.media_brief_service import MediaBriefService
from app.services.media_generation_service import MediaGenerationService

router = APIRouter(
    prefix="/projects/{project_id}/media-briefs",
    tags=["media-briefs"],
)


@router.get("", response_model=list[MediaBrief])
async def list_media_briefs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    content_asset_id: UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MediaBrief]:
    service = MediaBriefService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        content_asset_id=content_asset_id,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [media_brief_to_contract(row) for row in rows]


@router.get("/{brief_id}", response_model=MediaBrief)
async def get_media_brief(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaBrief:
    service = MediaBriefService(session)
    row = await service.get(current_user.id, project.id, brief_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media brief not found")
    return media_brief_to_contract(row)


@router.post("/{brief_id}/submit-review", response_model=MediaBrief)
async def submit_media_brief_for_review(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaBrief:
    service = MediaBriefService(session)
    try:
        updated = await service.submit_for_review(current_user.id, project.id, brief_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media brief not found")
    return media_brief_to_contract(updated)


@router.post("/{brief_id}/approve", response_model=MediaBrief)
async def approve_media_brief(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaBrief:
    service = MediaBriefService(session)
    try:
        updated = await service.approve_brief(current_user.id, project.id, brief_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media brief not found")
    return media_brief_to_contract(updated)


@router.post("/{brief_id}/archive", response_model=MediaBrief)
async def archive_media_brief(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaBrief:
    service = MediaBriefService(session)
    try:
        updated = await service.archive_brief(current_user.id, project.id, brief_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media brief not found")
    return media_brief_to_contract(updated)


@router.post(
    "/{brief_id}/generation-jobs",
    response_model=MediaGenerationJob,
    status_code=status.HTTP_201_CREATED,
)
async def create_media_generation_job_for_brief(
    brief_id: UUID,
    body: CreateMediaGenerationJobBody,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaGenerationJob:
    service = MediaGenerationService(session)
    try:
        row = await service.create_job_from_approved_brief(
            current_user.id,
            project.id,
            brief_id,
            provider=body.provider,
            media_type=body.media_type,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media brief not found")
    return media_generation_job_to_contract(row)


@router.post(
    "/{brief_id}/create-media-asset",
    response_model=CreateMediaAssetFromBriefResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_media_asset_from_brief(
    brief_id: UUID,
    body: CreateMediaAssetRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CreateMediaAssetFromBriefResponse:
    service = MediaAssetService(session)
    try:
        asset = await service.create_placeholder_from_approved_brief(
            current_user.id,
            project.id,
            brief_id,
            media_type=body.media_type,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media brief not found")
    media_type_value = (
        asset.media_type.value if hasattr(asset.media_type, "value") else str(asset.media_type)
    )
    status_value = asset.status.value if hasattr(asset.status, "value") else str(asset.status)
    return CreateMediaAssetFromBriefResponse(
        media_brief_id=brief_id,
        media_asset_id=asset.id,
        media_asset_status=status_value,
        media_type=media_type_value,
    )
