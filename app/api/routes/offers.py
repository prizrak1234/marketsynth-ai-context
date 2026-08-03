"""PRODUCT-01 — Offer artifact API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.db.models.user import UserTable
from app.product.offer_builder.service import OfferBuilderService
from app.schemas.contracts import (
    OfferArtifactDetail,
    OfferGenerateRequest,
    OfferGenerateResponse,
    OfferRecoverResponse,
    OfferReviewDecisionCreate,
    OfferRevisionRequestCreate,
    OfferVersionHistoryItem,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["offers"])


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    code = str(exc)
    if code in {
        "stale_approval_hash",
        "idempotency_key_required",
        "launch_pack_not_eligible",
        "invalid_workflow_transition",
        "invalid_review_state",
        "offer_already_approved",
        "offer_already_rejected",
        "offer_recovery_not_needed",
    }:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)
    if code.startswith("blocked_") or code.endswith("_not_found"):
        sc = status.HTTP_404_NOT_FOUND if code.endswith("_not_found") else status.HTTP_409_CONFLICT
        return HTTPException(status_code=sc, detail=code)
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)


@router.post(
    "/launch-packs/{launch_pack_id}/offer",
    response_model=OfferGenerateResponse,
)
async def generate_offer(
    project_id: UUID,
    launch_pack_id: UUID,
    body: OfferGenerateRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> OfferGenerateResponse:
    svc = OfferBuilderService(session, settings)
    try:
        return await svc.generate_for_launch_pack(
            current_user.id, project_id, launch_pack_id, body
        )
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc


@router.get(
    "/launch-packs/{launch_pack_id}/offer",
    response_model=OfferArtifactDetail,
)
async def get_launch_pack_offer(
    project_id: UUID,
    launch_pack_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> OfferArtifactDetail:
    svc = OfferBuilderService(session, settings)
    offer = await svc.get_offer_for_launch_pack(current_user.id, launch_pack_id)
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="offer_not_found")
    if offer.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="offer_not_found")
    return offer


@router.get("/offers/{offer_id}", response_model=OfferArtifactDetail)
async def get_offer_detail(
    project_id: UUID,
    offer_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> OfferArtifactDetail:
    svc = OfferBuilderService(session, settings)
    try:
        offer = await svc.get_offer(current_user.id, offer_id)
    except NotFoundError as exc:
        raise _map_error(exc) from exc
    if offer.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="offer_not_found")
    return offer


@router.get("/offers/{offer_id}/versions", response_model=list[OfferVersionHistoryItem])
async def list_offer_versions(
    project_id: UUID,
    offer_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> list[OfferVersionHistoryItem]:
    svc = OfferBuilderService(session, settings)
    try:
        offer = await svc.get_offer(current_user.id, offer_id)
        if offer.project_id != project_id:
            raise NotFoundError("offer_not_found")
        return await svc.list_versions(current_user.id, offer_id)
    except NotFoundError as exc:
        raise _map_error(exc) from exc


@router.post("/offers/{offer_id}/approve", response_model=OfferArtifactDetail)
async def approve_offer(
    project_id: UUID,
    offer_id: UUID,
    body: OfferReviewDecisionCreate,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> OfferArtifactDetail:
    svc = OfferBuilderService(session, settings)
    try:
        offer = await svc.approve(current_user.id, offer_id, body)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc
    if offer.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="offer_not_found")
    return offer


@router.post("/offers/{offer_id}/reject", response_model=OfferArtifactDetail)
async def reject_offer(
    project_id: UUID,
    offer_id: UUID,
    body: OfferReviewDecisionCreate,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> OfferArtifactDetail:
    svc = OfferBuilderService(session, settings)
    try:
        offer = await svc.reject(current_user.id, offer_id, body)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc
    if offer.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="offer_not_found")
    return offer


@router.post("/offers/{offer_id}/recover", response_model=OfferRecoverResponse)
async def recover_offer(
    project_id: UUID,
    offer_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> OfferRecoverResponse:
    svc = OfferBuilderService(session, settings)
    try:
        result = await svc.recover(current_user.id, offer_id)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc
    if result.offer.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="offer_not_found")
    return result


@router.post("/offers/{offer_id}/request-revision", response_model=OfferArtifactDetail)
async def request_offer_revision(
    project_id: UUID,
    offer_id: UUID,
    body: OfferRevisionRequestCreate,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> OfferArtifactDetail:
    svc = OfferBuilderService(session, settings)
    try:
        offer = await svc.request_revision(current_user.id, offer_id, body)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc
    if offer.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="offer_not_found")
    return offer
