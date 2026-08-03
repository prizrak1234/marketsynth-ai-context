"""Investigation API (Commercial MVP P0.2)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import investigation_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    Investigation,
    InvestigationCreateRequest,
    InvestigationStageId,
    InvestigationStageUpdateRequest,
    InvestigationStatus,
    InvestigationUpdateRequest,
)
from app.services.investigation_service import InvestigationService

router = APIRouter(
    prefix="/projects/{project_id}/investigations",
    tags=["investigations"],
)


class InvestigationBlockRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


def _map_conflict(exc: InvalidStateError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=Investigation, status_code=status.HTTP_201_CREATED)
async def create_investigation(
    body: InvestigationCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.create(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return investigation_to_contract(row)


@router.get("", response_model=list[Investigation])
async def list_investigations(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    status_filter: InvestigationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Investigation]:
    service = InvestigationService(session)
    rows = await service.list_investigations(
        current_user.id,
        project.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [investigation_to_contract(row) for row in rows]


@router.get("/latest", response_model=Investigation)
async def get_latest_investigation(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    row = await service.latest(current_user.id, project.id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.get("/{investigation_id}", response_model=Investigation)
async def get_investigation(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    row = await service.get(current_user.id, project.id, investigation_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.patch("/{investigation_id}", response_model=Investigation)
async def update_investigation(
    investigation_id: UUID,
    body: InvestigationUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.update(current_user.id, project.id, investigation_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.patch("/{investigation_id}/stages/{stage}", response_model=Investigation)
async def update_investigation_stage(
    investigation_id: UUID,
    stage: InvestigationStageId,
    body: InvestigationStageUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.update_stage(
            current_user.id,
            project.id,
            investigation_id,
            stage,
            body,
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.post("/{investigation_id}/start", response_model=Investigation)
async def start_investigation(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        # draft → ready → active convenience: mark ready then start if draft
        row = await service.get(current_user.id, project.id, investigation_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investigation not found",
            )
        if InvestigationStatus(row.status) == InvestigationStatus.DRAFT:
            await service.mark_ready(current_user.id, project.id, investigation_id)
        row = await service.start(current_user.id, project.id, investigation_id)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.post("/{investigation_id}/block", response_model=Investigation)
async def block_investigation(
    investigation_id: UUID,
    body: InvestigationBlockRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.block(
            current_user.id,
            project.id,
            investigation_id,
            reason=body.reason if body else None,
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.post("/{investigation_id}/resume", response_model=Investigation)
async def resume_investigation(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.resume(current_user.id, project.id, investigation_id)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.post("/{investigation_id}/submit-review", response_model=Investigation)
async def submit_investigation_review(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.submit_review(current_user.id, project.id, investigation_id)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.post("/{investigation_id}/complete", response_model=Investigation)
async def complete_investigation(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.complete(current_user.id, project.id, investigation_id)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.post("/{investigation_id}/cancel", response_model=Investigation)
async def cancel_investigation(
    investigation_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.cancel(current_user.id, project.id, investigation_id)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)


@router.post(
    "/{investigation_id}/supersede",
    response_model=Investigation,
    status_code=status.HTTP_201_CREATED,
)
async def supersede_investigation(
    investigation_id: UUID,
    body: InvestigationCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Investigation:
    service = InvestigationService(session)
    try:
        row = await service.supersede(
            current_user.id,
            project.id,
            investigation_id,
            body,
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return investigation_to_contract(row)
