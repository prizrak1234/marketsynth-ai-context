"""Content Director API — Text Golden Path (PRODUCT-CD-RUNTIME-01)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    ContentDirectorApproveRequest,
    ContentDirectorCandidateRead,
    ContentDirectorEditRequest,
    ContentDirectorGenerateRequest,
    ContentDirectorWorkspaceState,
    ContentRequestCreate,
    ContentRequestRead,
    ContentRequestUpdate,
    ContentRunRead,
)
from app.services.content_director_service import ContentDirectorService

router = APIRouter(
    prefix="/projects/{project_id}/content-director",
    tags=["content-director"],
)


@router.get("/workspace", response_model=ContentDirectorWorkspaceState)
async def get_content_director_workspace(
    request_id: UUID | None = Query(default=None),
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentDirectorWorkspaceState:
    service = ContentDirectorService(session)
    return await service.workspace_state(
        current_user.id, project.id, request_id=request_id
    )


@router.post(
    "/requests",
    response_model=ContentRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_request(
    body: ContentRequestCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentRequestRead:
    service = ContentDirectorService(session)
    created = await service.create_request(current_user.id, project.id, body)
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return created


@router.get("/requests", response_model=list[ContentRequestRead])
async def list_content_requests(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[ContentRequestRead]:
    service = ContentDirectorService(session)
    return await service.list_requests(current_user.id, project.id)


@router.get("/requests/{request_id}", response_model=ContentRequestRead)
async def get_content_request(
    request_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentRequestRead:
    service = ContentDirectorService(session)
    row = await service.get_request(current_user.id, project.id, request_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row


@router.patch("/requests/{request_id}", response_model=ContentRequestRead)
async def patch_content_request(
    request_id: UUID,
    body: ContentRequestUpdate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentRequestRead:
    service = ContentDirectorService(session)
    try:
        updated = await service.update_request(
            current_user.id, project.id, request_id, body
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return updated


@router.post("/requests/{request_id}/generate", response_model=ContentRunRead)
async def generate_content_variants(
    request_id: UUID,
    body: ContentDirectorGenerateRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentRunRead:
    service = ContentDirectorService(session)
    try:
        run = await service.generate(
            current_user.id, project.id, request_id, body or ContentDirectorGenerateRequest()
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return run


@router.post(
    "/requests/{request_id}/candidates/{asset_id}/reject",
    response_model=ContentDirectorCandidateRead,
)
async def reject_candidate(
    request_id: UUID,
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentDirectorCandidateRead:
    service = ContentDirectorService(session)
    result = await service.reject_candidate(
        current_user.id, project.id, request_id, asset_id
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return result


@router.patch(
    "/requests/{request_id}/candidates/{asset_id}",
    response_model=ContentDirectorCandidateRead,
)
async def edit_candidate(
    request_id: UUID,
    asset_id: UUID,
    body: ContentDirectorEditRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentDirectorCandidateRead:
    service = ContentDirectorService(session)
    try:
        result = await service.edit_candidate(
            current_user.id, project.id, request_id, asset_id, body
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return result


@router.post(
    "/requests/{request_id}/candidates/{asset_id}/approve",
    response_model=ContentDirectorCandidateRead,
)
async def approve_candidate(
    request_id: UUID,
    asset_id: UUID,
    body: ContentDirectorApproveRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentDirectorCandidateRead:
    service = ContentDirectorService(session)
    try:
        result = await service.approve_candidate(
            current_user.id,
            project.id,
            request_id,
            asset_id,
            body or ContentDirectorApproveRequest(),
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return result
