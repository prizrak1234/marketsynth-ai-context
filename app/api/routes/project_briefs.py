"""ProjectBrief API (Commercial MVP P0.1)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import project_brief_to_contract
from app.core.exceptions import DuplicateResourceError, InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    ProjectBrief,
    ProjectBriefCreateRequest,
    ProjectBriefStatus,
    ProjectBriefUpdateRequest,
)
from app.services.project_brief_service import ProjectBriefService

router = APIRouter(
    prefix="/projects/{project_id}/briefs",
    tags=["project-briefs"],
)


@router.post("", response_model=ProjectBrief, status_code=status.HTTP_201_CREATED)
async def create_project_brief(
    body: ProjectBriefCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ProjectBrief:
    service = ProjectBriefService(session)
    try:
        row = await service.create_draft(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project_brief_to_contract(row)


@router.get("", response_model=list[ProjectBrief])
async def list_project_briefs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    status_filter: ProjectBriefStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ProjectBrief]:
    service = ProjectBriefService(session)
    rows = await service.list_briefs(
        current_user.id,
        project.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [project_brief_to_contract(row) for row in rows]


@router.get("/latest", response_model=ProjectBrief)
async def get_latest_project_brief(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    prefer_submitted: bool = Query(default=True),
) -> ProjectBrief:
    service = ProjectBriefService(session)
    row = await service.latest(
        current_user.id,
        project.id,
        prefer_submitted=prefer_submitted,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project brief not found",
        )
    return project_brief_to_contract(row)


@router.get("/{brief_id}", response_model=ProjectBrief)
async def get_project_brief(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ProjectBrief:
    service = ProjectBriefService(session)
    row = await service.get(current_user.id, project.id, brief_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project brief not found",
        )
    return project_brief_to_contract(row)


@router.patch("/{brief_id}", response_model=ProjectBrief)
async def update_project_brief(
    brief_id: UUID,
    body: ProjectBriefUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ProjectBrief:
    service = ProjectBriefService(session)
    try:
        row = await service.update_draft(current_user.id, project.id, brief_id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project brief not found",
        )
    return project_brief_to_contract(row)


@router.post("/{brief_id}/submit", response_model=ProjectBrief)
async def submit_project_brief(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ProjectBrief:
    service = ProjectBriefService(session)
    try:
        row = await service.submit(current_user.id, project.id, brief_id)
    except DuplicateResourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project brief not found",
        )
    return project_brief_to_contract(row)


@router.post("/{brief_id}/supersede", response_model=ProjectBrief, status_code=status.HTTP_201_CREATED)
async def supersede_project_brief(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    body: ProjectBriefCreateRequest | None = None,
) -> ProjectBrief:
    service = ProjectBriefService(session)
    try:
        row = await service.supersede(current_user.id, project.id, brief_id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project brief not found",
        )
    return project_brief_to_contract(row)
