"""MarketingStrategy API (Commercial MVP P0.6).

GTM strategy — not MarketingPlan, Campaign, or execution approval.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import marketing_strategy_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    MarketingStrategy,
    MarketingStrategyBuildDraftRequest,
    MarketingStrategyCreate,
    MarketingStrategyLifecycleStatus,
    MarketingStrategyOrigin,
    MarketingStrategyReadinessStatus,
    MarketingStrategyReviewRequest,
    MarketingStrategyUpdate,
    VerdictKind,
)
from app.services.marketing_strategy_service import MarketingStrategyService

router = APIRouter(
    prefix="/projects/{project_id}/marketing-strategies",
    tags=["marketing-strategies"],
)


def _map_conflict(exc: InvalidStateError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=MarketingStrategy, status_code=status.HTTP_201_CREATED)
async def create_marketing_strategy(
    body: MarketingStrategyCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.create(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.post(
    "/build-draft",
    response_model=MarketingStrategy,
    status_code=status.HTTP_201_CREATED,
)
async def build_marketing_strategy_draft(
    body: MarketingStrategyBuildDraftRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.build_deterministic_draft(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.get("", response_model=list[MarketingStrategy])
async def list_marketing_strategies(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    lifecycle_status: MarketingStrategyLifecycleStatus | None = Query(default=None),
    verdict_id: UUID | None = Query(default=None),
    verdict_type: VerdictKind | None = Query(default=None),
    version: int | None = Query(default=None, ge=1),
    readiness_status: MarketingStrategyReadinessStatus | None = Query(default=None),
    origin: MarketingStrategyOrigin | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    approved_from: datetime | None = Query(default=None),
    approved_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[MarketingStrategy]:
    service = MarketingStrategyService(session)
    rows = await service.list_strategies(
        current_user.id,
        project.id,
        lifecycle_status=lifecycle_status,
        verdict_id=verdict_id,
        version=version,
        readiness_status=readiness_status,
        origin=origin,
        created_from=created_from,
        created_to=created_to,
        approved_from=approved_from,
        approved_to=approved_to,
        limit=limit,
        offset=offset,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if verdict_type is not None:
        rows = [r for r in rows if VerdictKind(r.business_verdict_type) == verdict_type]
    return [marketing_strategy_to_contract(r) for r in rows]


@router.get("/latest", response_model=MarketingStrategy)
async def get_latest_marketing_strategy(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    row = await service.get_latest(current_user.id, project.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.get("/{strategy_id}", response_model=MarketingStrategy)
async def get_marketing_strategy(
    strategy_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    row = await service.get(current_user.id, project.id, strategy_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.patch("/{strategy_id}", response_model=MarketingStrategy)
async def patch_marketing_strategy(
    strategy_id: UUID,
    body: MarketingStrategyUpdate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.update_draft(current_user.id, project.id, strategy_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.post("/{strategy_id}/submit-review", response_model=MarketingStrategy)
async def submit_marketing_strategy_review(
    strategy_id: UUID,
    body: MarketingStrategyReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.submit_review(
            current_user.id, project.id, strategy_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.post("/{strategy_id}/approve", response_model=MarketingStrategy)
async def approve_marketing_strategy(
    strategy_id: UUID,
    body: MarketingStrategyReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.approve(
            current_user.id, project.id, strategy_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.post("/{strategy_id}/reject", response_model=MarketingStrategy)
async def reject_marketing_strategy(
    strategy_id: UUID,
    body: MarketingStrategyReviewRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.reject(
            current_user.id, project.id, strategy_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.post("/{strategy_id}/return-draft", response_model=MarketingStrategy)
async def return_marketing_strategy_draft(
    strategy_id: UUID,
    body: MarketingStrategyReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.return_draft(
            current_user.id, project.id, strategy_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.post("/{strategy_id}/archive", response_model=MarketingStrategy)
async def archive_marketing_strategy(
    strategy_id: UUID,
    body: MarketingStrategyReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.archive(
            current_user.id, project.id, strategy_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)


@router.post(
    "/{strategy_id}/supersede",
    response_model=MarketingStrategy,
    status_code=status.HTTP_201_CREATED,
)
async def supersede_marketing_strategy(
    strategy_id: UUID,
    body: MarketingStrategyCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingStrategy:
    service = MarketingStrategyService(session)
    try:
        row = await service.supersede(
            current_user.id, project.id, strategy_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return marketing_strategy_to_contract(row)
