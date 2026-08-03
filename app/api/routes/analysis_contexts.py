"""PRODUCT-01.3A — analysis context intake gate API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.db.models.user import UserTable
from app.schemas.contracts import (
    AnalysisContextConfirmRequest,
    AnalysisContextCreateDraftRequest,
    AnalysisContextCurrentResponse,
    AnalysisContextEditRequest,
    AnalysisContextRecord,
    AnalysisContextStartNewResponse,
)
from app.services.analysis_context_service import AnalysisContextService

router = APIRouter(
    prefix="/projects/{project_id}/analysis-contexts",
    tags=["analysis-contexts"],
)


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    code = str(exc)
    status_code = status.HTTP_409_CONFLICT
    if code == "analysis_context_incomplete":
        status_code = status.HTTP_400_BAD_REQUEST
    return HTTPException(status_code=status_code, detail=code)


@router.post("", response_model=AnalysisContextRecord, status_code=status.HTTP_201_CREATED)
async def analysis_context_create_draft(
    project_id: UUID,
    body: AnalysisContextCreateDraftRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> AnalysisContextRecord:
    svc = AnalysisContextService(session, settings)
    try:
        return await svc.create_draft(current_user.id, project_id, body)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc


@router.get("/current", response_model=AnalysisContextCurrentResponse)
async def analysis_context_get_current(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> AnalysisContextCurrentResponse:
    svc = AnalysisContextService(session, settings)
    try:
        return await svc.get_current(current_user.id, project_id)
    except NotFoundError as exc:
        raise _map_error(exc) from exc


@router.post("/{context_id}/confirm", response_model=AnalysisContextRecord)
async def analysis_context_confirm(
    project_id: UUID,
    context_id: UUID,
    body: AnalysisContextConfirmRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> AnalysisContextRecord:
    svc = AnalysisContextService(session, settings)
    try:
        return await svc.confirm(current_user.id, project_id, context_id, body)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc


@router.post("/{context_id}/edit", response_model=AnalysisContextRecord)
async def analysis_context_edit(
    project_id: UUID,
    context_id: UUID,
    body: AnalysisContextEditRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> AnalysisContextRecord:
    svc = AnalysisContextService(session, settings)
    try:
        return await svc.edit(current_user.id, project_id, context_id, body)
    except NotFoundError as exc:
        raise _map_error(exc) from exc


@router.post("/start-new", response_model=AnalysisContextStartNewResponse)
async def analysis_context_start_new(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> AnalysisContextStartNewResponse:
    svc = AnalysisContextService(session, settings)
    try:
        return await svc.start_new(current_user.id, project_id)
    except NotFoundError as exc:
        raise _map_error(exc) from exc
