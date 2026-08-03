"""Media generation jobs API — gated providers, no publishing (Phase AI.56–AI.58)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import media_generation_job_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.media_generation.contracts import MediaGenerationJob
from app.schemas.media_generation import CreateMediaGenerationJobBody
from app.services.media_generation_service import MediaGenerationService

router = APIRouter(
    prefix="/projects/{project_id}/media-generation-jobs",
    tags=["media-generation"],
)


@router.get("", response_model=list[MediaGenerationJob])
async def list_media_generation_jobs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    media_brief_id: UUID = Query(...),
) -> list[MediaGenerationJob]:
    service = MediaGenerationService(session)
    rows = await service.list_jobs_for_brief(
        current_user.id,
        project.id,
        media_brief_id,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media brief not found")
    return [media_generation_job_to_contract(row) for row in rows]


@router.get("/{job_id}", response_model=MediaGenerationJob)
async def get_media_generation_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaGenerationJob:
    service = MediaGenerationService(session)
    row = await service.get_job(current_user.id, project.id, job_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media generation job not found",
        )
    return media_generation_job_to_contract(row)


@router.post(
    "",
    response_model=MediaGenerationJob,
    status_code=status.HTTP_201_CREATED,
)
async def create_media_generation_job(
    body: CreateMediaGenerationJobBody,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    media_brief_id: UUID = Query(...),
) -> MediaGenerationJob:
    service = MediaGenerationService(session)
    try:
        row = await service.create_job_from_approved_brief(
            current_user.id,
            project.id,
            media_brief_id,
            provider=body.provider,
            media_type=body.media_type,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media brief not found")
    return media_generation_job_to_contract(row)


@router.post("/{job_id}/start", response_model=MediaGenerationJob)
async def start_media_generation_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaGenerationJob:
    service = MediaGenerationService(session)
    try:
        row = await service.start_job(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media generation job not found",
        )
    return media_generation_job_to_contract(row)


@router.post("/{job_id}/complete-mock", response_model=MediaGenerationJob)
async def complete_mock_media_generation_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaGenerationJob:
    service = MediaGenerationService(session)
    try:
        row = await service.complete_mock_job(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media generation job not found",
        )
    return media_generation_job_to_contract(row)


@router.post("/{job_id}/execute", response_model=MediaGenerationJob)
async def execute_media_generation_job(
    job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MediaGenerationJob:
    service = MediaGenerationService(session)
    try:
        row = await service.execute_job(current_user.id, project.id, job_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media generation job not found",
        )
    return media_generation_job_to_contract(row)
