"""Visual Director API — Image Golden Path (PRODUCT-CD-RUNTIME-02)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    VisualDirectorApproveRequest,
    VisualDirectorCandidateRead,
    VisualDirectorGenerateRequest,
    VisualDirectorWorkspaceState,
    VisualRequestCreate,
    VisualRequestRead,
    VisualRequestUpdate,
    VisualRunRead,
)
from app.services.visual_director_service import VisualDirectorService

router = APIRouter(
    prefix="/projects/{project_id}/visual-director",
    tags=["visual-director"],
)


@router.get("/workspace", response_model=VisualDirectorWorkspaceState)
async def get_visual_director_workspace(
    request_id: UUID | None = Query(default=None),
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VisualDirectorWorkspaceState:
    service = VisualDirectorService(session)
    return await service.workspace_state(
        current_user.id, project.id, request_id=request_id
    )


@router.post(
    "/requests",
    response_model=VisualRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_visual_request(
    body: VisualRequestCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VisualRequestRead:
    service = VisualDirectorService(session)
    try:
        created = await service.create_request(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return created


@router.get("/requests", response_model=list[VisualRequestRead])
async def list_visual_requests(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[VisualRequestRead]:
    service = VisualDirectorService(session)
    return await service.list_requests(current_user.id, project.id)


@router.get("/requests/{request_id}", response_model=VisualRequestRead)
async def get_visual_request(
    request_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VisualRequestRead:
    service = VisualDirectorService(session)
    row = await service.get_request(current_user.id, project.id, request_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row


@router.patch("/requests/{request_id}", response_model=VisualRequestRead)
async def patch_visual_request(
    request_id: UUID,
    body: VisualRequestUpdate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VisualRequestRead:
    service = VisualDirectorService(session)
    try:
        updated = await service.update_request(
            current_user.id, project.id, request_id, body
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return updated


@router.post("/requests/{request_id}/generate", response_model=VisualRunRead)
async def generate_visual_variants(
    request_id: UUID,
    body: VisualDirectorGenerateRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VisualRunRead:
    service = VisualDirectorService(session)
    try:
        run = await service.generate(
            current_user.id,
            project.id,
            request_id,
            body or VisualDirectorGenerateRequest(),
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return run


@router.post(
    "/requests/{request_id}/candidates/{asset_id}/reject",
    response_model=VisualDirectorCandidateRead,
)
async def reject_visual_candidate(
    request_id: UUID,
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VisualDirectorCandidateRead:
    service = VisualDirectorService(session)
    result = await service.reject_candidate(
        current_user.id, project.id, request_id, asset_id
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return result


@router.post(
    "/requests/{request_id}/candidates/{asset_id}/approve",
    response_model=VisualDirectorCandidateRead,
)
async def approve_visual_candidate(
    request_id: UUID,
    asset_id: UUID,
    body: VisualDirectorApproveRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VisualDirectorCandidateRead:
    service = VisualDirectorService(session)
    try:
        result = await service.approve_candidate(
            current_user.id,
            project.id,
            request_id,
            asset_id,
            body or VisualDirectorApproveRequest(),
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return result


@router.get("/candidates/{asset_id}/content")
async def get_visual_candidate_content(
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> FileResponse:
    service = VisualDirectorService(session)
    resolved = await service.resolve_content_path(
        current_user.id, project.id, asset_id
    )
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    path_str, mime = resolved
    path = Path(path_str)
    return FileResponse(
        path,
        media_type=mime,
        filename=path.name,
    )
