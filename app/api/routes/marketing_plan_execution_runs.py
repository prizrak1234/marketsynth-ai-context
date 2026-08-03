"""Marketing plan execution run API (Phase AI.29)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    marketing_plan_execution_run_to_contract,
    marketing_specialist_output_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    ExecuteMarketingSpecialistTaskResponse,
    MarketingPlanExecutionRun,
    MarketingPlanExecutionStatus,
    MarketingSpecialistOutput,
)
from app.services.marketing_plan_execution_service import MarketingPlanExecutionService
from app.services.marketing_specialist_output_service import MarketingSpecialistOutputService
from app.services.specialist_execution_service import SpecialistExecutionService

router = APIRouter(
    prefix="/projects/{project_id}/marketing-plan-execution-runs",
    tags=["marketing-plan-execution-runs"],
)


@router.get("", response_model=list[MarketingPlanExecutionRun])
async def list_marketing_plan_execution_runs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    marketing_plan_id: UUID | None = None,
    status_filter: MarketingPlanExecutionStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[MarketingPlanExecutionRun]:
    service = MarketingPlanExecutionService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        marketing_plan_id=marketing_plan_id,
        status=status_filter,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [marketing_plan_execution_run_to_contract(row) for row in rows]


@router.get("/{run_id}", response_model=MarketingPlanExecutionRun)
async def get_marketing_plan_execution_run(
    run_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlanExecutionRun:
    service = MarketingPlanExecutionService(session)
    row = await service.get(current_user.id, project.id, run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan execution run not found",
        )
    return marketing_plan_execution_run_to_contract(row)


@router.post("/{run_id}/start", response_model=MarketingPlanExecutionRun)
async def start_marketing_plan_execution_run(
    run_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlanExecutionRun:
    service = MarketingPlanExecutionService(session)
    try:
        row = await service.start(current_user.id, project.id, run_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan execution run not found",
        )
    return marketing_plan_execution_run_to_contract(row)


@router.post(
    "/{run_id}/complete-placeholder",
    response_model=MarketingPlanExecutionRun,
)
async def complete_placeholder_marketing_plan_execution_run(
    run_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlanExecutionRun:
    service = MarketingPlanExecutionService(session)
    try:
        row = await service.complete_placeholder(current_user.id, project.id, run_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan execution run not found",
        )
    return marketing_plan_execution_run_to_contract(row)


@router.post(
    "/{run_id}/task-outputs/{task_index}/placeholder",
    response_model=MarketingSpecialistOutput,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_placeholder_specialist_output(
    run_id: UUID,
    task_index: int,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingSpecialistOutput:
    if task_index < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="task_index must be >= 0",
        )
    service = MarketingSpecialistOutputService(session)
    try:
        row = await service.create_placeholder_output(
            current_user.id,
            project.id,
            run_id,
            task_index,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan execution run not found",
        )
    return marketing_specialist_output_to_contract(row)


@router.post(
    "/{run_id}/tasks/{task_index}/execute-specialist",
    response_model=ExecuteMarketingSpecialistTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_specialist_task(
    run_id: UUID,
    task_index: int,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ExecuteMarketingSpecialistTaskResponse:
    if task_index < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="task_index must be >= 0",
        )
    service = SpecialistExecutionService(session)
    try:
        result = await service.execute_task_specialist(
            current_user.id,
            project.id,
            run_id,
            task_index,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan execution run not found",
        )
    return ExecuteMarketingSpecialistTaskResponse(
        execution_run_id=run_id,
        task_index=task_index,
        specialist=result.specialist,
        specialist_output_id=result.specialist_output_id,
        status=result.status,
        safe_summary=result.safe_summary,
        execution_run_status=result.execution_run_status,
        run_completed=result.run_completed,
    )


@router.post("/{run_id}/cancel", response_model=MarketingPlanExecutionRun)
async def cancel_marketing_plan_execution_run(
    run_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlanExecutionRun:
    service = MarketingPlanExecutionService(session)
    try:
        row = await service.cancel(current_user.id, project.id, run_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing plan execution run not found",
        )
    return marketing_plan_execution_run_to_contract(row)
