"""Phase 1B.1 — commercial research orchestration API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError, NotFoundError, OwnershipError
from app.db.models.user import UserTable
from app.schemas.contracts import (
    CommercialResearchApproveRequest,
    CommercialResearchApproveResponse,
    CommercialResearchExecuteRequest,
    CommercialResearchExecuteResponse,
    CommercialResearchPreflightResponse,
    CommercialResearchQuoteResponse,
    CommercialResearchStatusResponse,
)
from app.services.commercial_research_pipeline_service import CommercialResearchPipelineService

router = APIRouter(
    prefix="/user-requests/{user_request_id}/commercial-research",
    tags=["commercial-research"],
)


class CommercialResearchStageBody(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=128)


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, OwnershipError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    code = str(exc)
    status_code = status.HTTP_409_CONFLICT
    if code in {
        "owner_confirmation_required",
        "idempotency_key_required",
    }:
        status_code = status.HTTP_400_BAD_REQUEST
    if code in {
        "approval_required",
        "approval_invalid",
        "approval_mismatch",
        "approval_quote_mismatch",
        "approval_request_hash_mismatch",
        "approval_expired",
        "quote_expired",
        "quote_mismatch",
        "quote_request_hash_mismatch",
        "execution_not_enabled_in_phase_1b_1",
        "outcome_unknown_no_blind_retry",
        "retry_not_allowed",
        "preflight_required",
        "preflight_not_ready",
        "quote_required",
    }:
        status_code = status.HTTP_409_CONFLICT
    if code == "commercial_research_run_not_found":
        status_code = status.HTTP_404_NOT_FOUND
    return HTTPException(status_code=status_code, detail=code)


@router.post("/preflight", response_model=CommercialResearchPreflightResponse)
async def commercial_research_preflight(
    user_request_id: UUID,
    body: CommercialResearchStageBody | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> CommercialResearchPreflightResponse:
    svc = CommercialResearchPipelineService(session, settings)
    key = (body.idempotency_key if body else None) or idempotency_key
    try:
        return await svc.preflight(
            current_user.id,
            user_request_id,
            idempotency_key=key,
        )
    except (InvalidStateError, NotFoundError, OwnershipError) as exc:
        raise _map_error(exc) from exc


@router.post("/quote", response_model=CommercialResearchQuoteResponse)
async def commercial_research_quote(
    user_request_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> CommercialResearchQuoteResponse:
    svc = CommercialResearchPipelineService(session, settings)
    try:
        return await svc.quote(current_user.id, user_request_id)
    except (InvalidStateError, NotFoundError, OwnershipError) as exc:
        raise _map_error(exc) from exc


@router.post("/approve", response_model=CommercialResearchApproveResponse)
async def commercial_research_approve(
    user_request_id: UUID,
    body: CommercialResearchApproveRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> CommercialResearchApproveResponse:
    svc = CommercialResearchPipelineService(session, settings)
    try:
        return await svc.approve(
            current_user.id,
            user_request_id,
            quote_id=body.quote_id,
            owner_confirmed=body.owner_confirmed,
        )
    except (InvalidStateError, NotFoundError, OwnershipError) as exc:
        raise _map_error(exc) from exc


@router.post("/execute", response_model=CommercialResearchExecuteResponse)
async def commercial_research_execute(
    user_request_id: UUID,
    body: CommercialResearchExecuteRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> CommercialResearchExecuteResponse:
    svc = CommercialResearchPipelineService(session, settings)
    key = body.idempotency_key or idempotency_key or ""
    try:
        return await svc.execute(
            current_user.id,
            user_request_id,
            idempotency_key=key,
            owner_confirmed=body.owner_confirmed,
        )
    except InvalidStateError as exc:
        raise _map_error(exc) from exc
    except (NotFoundError, OwnershipError) as exc:
        raise _map_error(exc) from exc


@router.get("/status", response_model=CommercialResearchStatusResponse)
async def commercial_research_status(
    user_request_id: UUID,
    developer: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> CommercialResearchStatusResponse:
    svc = CommercialResearchPipelineService(session, settings)
    try:
        return await svc.status(
            current_user.id,
            user_request_id,
            include_developer=developer,
        )
    except InvalidStateError as exc:
        raise _map_error(exc) from exc
    except (NotFoundError, OwnershipError) as exc:
        raise _map_error(exc) from exc
