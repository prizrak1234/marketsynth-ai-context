"""Marketing scenario templates API (Phase AI.129)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import marketing_plan_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.marketing.scenarios import get_scenario, list_scenarios
from app.schemas.contracts import MarketingPlan, ScenarioTemplate
from app.services.marketing_plan_service import MarketingPlanService

router = APIRouter(
    prefix="/projects/{project_id}/marketing-scenarios",
    tags=["marketing-scenarios"],
)


@router.get("", response_model=list[ScenarioTemplate])
async def list_marketing_scenarios(
    project: ProjectTable = Depends(require_project_owner),
) -> list[ScenarioTemplate]:
    _ = project
    return list_scenarios()


@router.get("/{scenario_id}", response_model=ScenarioTemplate)
async def get_marketing_scenario(
    scenario_id: str,
    project: ProjectTable = Depends(require_project_owner),
) -> ScenarioTemplate:
    _ = project
    template = get_scenario(scenario_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing scenario not found",
        )
    return template


@router.post(
    "/{scenario_id}/create-plan",
    response_model=MarketingPlan,
    status_code=status.HTTP_201_CREATED,
)
async def create_marketing_plan_from_scenario(
    scenario_id: str,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingPlan:
    if get_scenario(scenario_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing scenario not found",
        )

    service = MarketingPlanService(session)
    try:
        row = await service.create_from_scenario(
            current_user.id,
            project.id,
            scenario_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return marketing_plan_to_contract(row)
