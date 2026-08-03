"""Scenario wizard runs API (Phase AI.139)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import scenario_wizard_run_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.marketing.scenarios import get_scenario
from app.schemas.contracts import ScenarioWizardRun, ScenarioWizardRunStatus
from app.services.scenario_wizard_service import ScenarioWizardService

router = APIRouter(
    prefix="/projects/{project_id}/scenario-wizard-runs",
    tags=["scenario-wizard-runs"],
)


class CreateScenarioWizardRunRequest(BaseModel):
    scenario_id: str = Field(..., min_length=1, max_length=128)


@router.get("", response_model=list[ScenarioWizardRun])
async def list_scenario_wizard_runs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    status_filter: ScenarioWizardRunStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[ScenarioWizardRun]:
    service = ScenarioWizardService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        status=status_filter,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [scenario_wizard_run_to_contract(row) for row in rows]


@router.post("", response_model=ScenarioWizardRun, status_code=status.HTTP_201_CREATED)
async def create_scenario_wizard_run(
    body: CreateScenarioWizardRunRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ScenarioWizardRun:
    if get_scenario(body.scenario_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing scenario not found",
        )
    service = ScenarioWizardService(session)
    row = await service.create_run(current_user.id, project.id, body.scenario_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return scenario_wizard_run_to_contract(row)


@router.get("/{run_id}", response_model=ScenarioWizardRun)
async def get_scenario_wizard_run(
    run_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ScenarioWizardRun:
    service = ScenarioWizardService(session)
    row = await service.get(current_user.id, project.id, run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario wizard run not found",
        )
    return scenario_wizard_run_to_contract(row)


@router.post("/{run_id}/advance", response_model=ScenarioWizardRun)
async def advance_scenario_wizard_run(
    run_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ScenarioWizardRun:
    service = ScenarioWizardService(session)
    try:
        row = await service.advance(current_user.id, project.id, run_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario wizard run not found",
        )
    return scenario_wizard_run_to_contract(row)
