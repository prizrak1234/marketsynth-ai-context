"""ImplementationPlan API (Commercial MVP P1.1).

Project delivery plan — not MarketingPlan, Campaign, or execution approval.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import implementation_plan_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    ImplementationMarketingPlanHandoffConfirmRequest,
    ImplementationMarketingPlanHandoffConfirmResponse,
    ImplementationMarketingPlanHandoffPreviewResponse,
    ImplementationPlan,
    ImplementationPlanBuildDraftRequest,
    ImplementationPlanCreate,
    ImplementationPlanHandoffPreview,
    ImplementationPlanLifecycleStatus,
    ImplementationPlanOrigin,
    ImplementationPlanReadinessStatus,
    ImplementationPlanReviewRequest,
    ImplementationPlanUpdate,
)
from app.services.implementation_marketing_plan_handoff_service import (
    ImplementationMarketingPlanHandoffService,
)
from app.services.implementation_plan_service import ImplementationPlanService

router = APIRouter(
    prefix="/projects/{project_id}/implementation-plans",
    tags=["implementation-plans"],
)


def _map_conflict(exc: InvalidStateError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=ImplementationPlan, status_code=status.HTTP_201_CREATED)
async def create_implementation_plan(
    body: ImplementationPlanCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.create(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post(
    "/build-draft",
    response_model=ImplementationPlan,
    status_code=status.HTTP_201_CREATED,
)
async def build_implementation_plan_draft(
    body: ImplementationPlanBuildDraftRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.build_deterministic_draft(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.get("", response_model=list[ImplementationPlan])
async def list_implementation_plans(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    lifecycle_status: ImplementationPlanLifecycleStatus | None = Query(default=None),
    readiness_status: ImplementationPlanReadinessStatus | None = Query(default=None),
    strategy_id: UUID | None = Query(default=None),
    strategy_version: int | None = Query(default=None, ge=1),
    version: int | None = Query(default=None, ge=1),
    origin: ImplementationPlanOrigin | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    approved_from: datetime | None = Query(default=None),
    approved_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ImplementationPlan]:
    service = ImplementationPlanService(session)
    rows = await service.list_plans(
        current_user.id,
        project.id,
        lifecycle_status=lifecycle_status,
        readiness_status=readiness_status,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        version=version,
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
    return [implementation_plan_to_contract(r) for r in rows]


@router.get("/latest", response_model=ImplementationPlan)
async def get_latest_implementation_plan(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    row = await service.get_latest(current_user.id, project.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.get("/{plan_id}", response_model=ImplementationPlan)
async def get_implementation_plan(
    plan_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    row = await service.get(current_user.id, project.id, plan_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.patch("/{plan_id}", response_model=ImplementationPlan)
async def patch_implementation_plan(
    plan_id: UUID,
    body: ImplementationPlanUpdate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.update_draft(current_user.id, project.id, plan_id, body)
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.get("/{plan_id}/handoff-preview", response_model=ImplementationPlanHandoffPreview)
async def get_implementation_handoff_preview(
    plan_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlanHandoffPreview:
    service = ImplementationPlanService(session)
    preview = await service.handoff_preview(current_user.id, project.id, plan_id)
    if preview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return preview


@router.post("/{plan_id}/submit-review", response_model=ImplementationPlan)
async def submit_implementation_plan_review(
    plan_id: UUID,
    body: ImplementationPlanReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.submit_review(
            current_user.id, project.id, plan_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post("/{plan_id}/approve", response_model=ImplementationPlan)
async def approve_implementation_plan(
    plan_id: UUID,
    body: ImplementationPlanReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.approve(
            current_user.id, project.id, plan_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post("/{plan_id}/reject", response_model=ImplementationPlan)
async def reject_implementation_plan(
    plan_id: UUID,
    body: ImplementationPlanReviewRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.reject(
            current_user.id, project.id, plan_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post("/{plan_id}/return-draft", response_model=ImplementationPlan)
async def return_implementation_plan_draft(
    plan_id: UUID,
    body: ImplementationPlanReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.return_draft(
            current_user.id, project.id, plan_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post("/{plan_id}/block", response_model=ImplementationPlan)
async def block_implementation_plan(
    plan_id: UUID,
    body: ImplementationPlanReviewRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.block(
            current_user.id, project.id, plan_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post("/{plan_id}/unblock", response_model=ImplementationPlan)
async def unblock_implementation_plan(
    plan_id: UUID,
    body: ImplementationPlanReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.unblock(
            current_user.id, project.id, plan_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post("/{plan_id}/archive", response_model=ImplementationPlan)
async def archive_implementation_plan(
    plan_id: UUID,
    body: ImplementationPlanReviewRequest | None = None,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.archive(
            current_user.id, project.id, plan_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post(
    "/{plan_id}/supersede",
    response_model=ImplementationPlan,
    status_code=status.HTTP_201_CREATED,
)
async def supersede_implementation_plan(
    plan_id: UUID,
    body: ImplementationPlanCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationPlan:
    service = ImplementationPlanService(session)
    try:
        row = await service.supersede(
            current_user.id, project.id, plan_id, current_user.id, body
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return implementation_plan_to_contract(row)


@router.post(
    "/{plan_id}/marketing-plan-handoff/preview",
    response_model=ImplementationMarketingPlanHandoffPreviewResponse,
)
async def preview_marketing_plan_handoff(
    plan_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationMarketingPlanHandoffPreviewResponse:
    """P1.2 — immutable mapping preview; does not create MarketingPlan."""
    service = ImplementationMarketingPlanHandoffService(session)
    try:
        preview = await service.preview(
            current_user.id, project.id, plan_id, actor_id=current_user.id
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if preview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return preview


@router.post(
    "/{plan_id}/marketing-plan-handoff/confirm",
    response_model=ImplementationMarketingPlanHandoffConfirmResponse,
)
async def confirm_marketing_plan_handoff(
    plan_id: UUID,
    body: ImplementationMarketingPlanHandoffConfirmRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ImplementationMarketingPlanHandoffConfirmResponse:
    """P1.2 — explicit confirm creates MarketingPlan draft only (no approve/dispatch)."""
    service = ImplementationMarketingPlanHandoffService(session)
    try:
        result = await service.confirm(
            current_user.id,
            project.id,
            plan_id,
            body,
            actor_id=current_user.id,
        )
    except InvalidStateError as exc:
        raise _map_conflict(exc) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return result
