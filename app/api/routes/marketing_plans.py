"""Marketing plans API (Phase AI.28)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    marketing_plan_execution_run_to_contract,
    marketing_plan_to_contract,
    marketing_plan_version_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    MarketingPlan,
    MarketingPlanExecutionRun,
    MarketingPlanStatus,
    MarketingPlanVersion,
)
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_plan_service import MarketingPlanService

router = APIRouter(
    prefix="/projects/{project_id}/marketing-plans",
    tags=["marketing-plans"],
)


@router.get("", response_model=list[MarketingPlan])
async def list_marketing_plans(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    status_filter: MarketingPlanStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[MarketingPlan]:
    service = MarketingPlanService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        status=status_filter,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [marketing_plan_to_contract(row) for row in rows]


@router.get("/{plan_id}", response_model=MarketingPlan)
async def get_marketing_plan(
    plan_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlan:
    service = MarketingPlanService(session)
    row = await service.get(current_user.id, project.id, plan_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan not found",
        )
    return marketing_plan_to_contract(row)


@router.post("/{plan_id}/approve", response_model=MarketingPlan)
async def approve_marketing_plan(
    plan_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlan:
    service = MarketingPlanService(session)
    try:
        row = await service.approve(current_user.id, project.id, plan_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan not found",
        )
    return marketing_plan_to_contract(row)


@router.post("/{plan_id}/archive", response_model=MarketingPlan)
async def archive_marketing_plan(
    plan_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlan:
    service = MarketingPlanService(session)
    try:
        row = await service.archive(current_user.id, project.id, plan_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan not found",
        )
    return marketing_plan_to_contract(row)


@router.post(
    "/{plan_id}/execution-runs",
    response_model=MarketingPlanExecutionRun,
    status_code=status.HTTP_201_CREATED,
)
async def create_marketing_plan_execution_run(
    plan_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlanExecutionRun:
    service = MarketingPlanExecutionService(session)
    try:
        row = await service.create_from_approved_plan(
            current_user.id,
            project.id,
            plan_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan not found",
        )
    return marketing_plan_execution_run_to_contract(row)


@router.get("/{plan_id}/versions", response_model=list[MarketingPlanVersion])
async def list_marketing_plan_versions(
    plan_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[MarketingPlanVersion]:
    service = MarketingPlanService(session)
    rows = await service.list_versions(current_user.id, project.id, plan_id)
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan not found",
        )
    return [marketing_plan_version_to_contract(row) for row in rows]


@router.get("/{plan_id}/versions/{version_number}", response_model=MarketingPlanVersion)
async def get_marketing_plan_version(
    plan_id: UUID,
    version_number: int,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlanVersion:
    if version_number < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="version_number must be >= 1",
        )
    service = MarketingPlanService(session)
    row = await service.get_version(
        current_user.id,
        project.id,
        plan_id,
        version_number,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan version not found",
        )
    return marketing_plan_version_to_contract(row)
