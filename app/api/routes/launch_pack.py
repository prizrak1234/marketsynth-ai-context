"""CWF.1a — Launch Pack decision and request API."""

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
    CommercialNextStepDecisionCreate,
    CommercialNextStepSubmitResponse,
    LaunchPackJourneyHydration,
)
from app.services.launch_pack_service import LaunchPackService

router = APIRouter(
    prefix="/projects/{project_id}/launch-pack",
    tags=["launch-pack"],
)


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    code = str(exc)
    status_code = status.HTTP_409_CONFLICT
    if code in {
        "idempotency_key_required",
        "conditions_required",
        "risk_override_required",
        "action_not_allowed_for_verdict",
    }:
        status_code = status.HTTP_400_BAD_REQUEST
    if code in {"launch_pack_not_allowed", "launch_pack_already_requested"}:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=code)


@router.get("/journey", response_model=LaunchPackJourneyHydration)
async def launch_pack_journey(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> LaunchPackJourneyHydration:
    svc = LaunchPackService(session, settings)
    result = await svc.get_journey(current_user.id, project_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="validation_not_found")
    return result


@router.post("/next-step", response_model=CommercialNextStepSubmitResponse)
async def launch_pack_next_step(
    project_id: UUID,
    body: CommercialNextStepDecisionCreate,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> CommercialNextStepSubmitResponse:
    svc = LaunchPackService(session, settings)
    try:
        return await svc.submit_next_step(current_user.id, project_id, body)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc
