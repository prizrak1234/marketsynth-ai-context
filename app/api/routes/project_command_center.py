"""Project Command Center API — summary + General recommend-only chat."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.core.exceptions import NotFoundError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    PccGeneralConversation,
    PccGeneralSendRequest,
    PccGeneralSendResponse,
    ProjectCommandCenterSummary,
)
from app.services.project_command_center_service import ProjectCommandCenterService

router = APIRouter(
    prefix="/projects/{project_id}/command-center",
    tags=["project-command-center"],
)


@router.get("", response_model=ProjectCommandCenterSummary)
async def get_project_command_center(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ProjectCommandCenterSummary:
    service = ProjectCommandCenterService(session)
    try:
        return await service.get_summary(current_user.id, project.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/general", response_model=PccGeneralConversation)
async def get_project_general(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PccGeneralConversation:
    service = ProjectCommandCenterService(session)
    try:
        return await service.get_general(current_user.id, project.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/general/messages", response_model=PccGeneralSendResponse)
async def send_project_general_message(
    body: PccGeneralSendRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PccGeneralSendResponse:
    service = ProjectCommandCenterService(session)
    try:
        return await service.send_general(current_user.id, project.id, body.message)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
