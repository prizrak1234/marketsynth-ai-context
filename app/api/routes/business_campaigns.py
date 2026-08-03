"""Business campaign layer API (Phase AI.148–AI.153)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import campaign_to_contract, scenario_wizard_run_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    Campaign,
    CampaignActionResult,
    CampaignActionType,
    CampaignControlCenter,
    CampaignControlCenterSummary,
    CampaignDashboard,
    CampaignHealthStatus,
    CampaignMetrics,
    CampaignNextActionType,
    CampaignStatus,
    CampaignSupervisorReport,
    CampaignWorkflowRun,
    CampaignWorkflowTemplate,
    ScenarioWizardRun,
)
from app.services.campaign_action_executor_service import CampaignActionExecutorService
from app.services.campaign_control_center_service import CampaignControlCenterService
from app.services.campaign_layer_service import CampaignLayerService
from app.services.campaign_supervisor_service import CampaignSupervisorService
from app.services.campaign_workflow_service import CampaignWorkflowService
from app.services.scenario_wizard_service import ScenarioWizardService

router = APIRouter(
    prefix="/projects/{project_id}/business-campaigns",
    tags=["business-campaigns"],
)


class CreateBusinessCampaignRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    goal: str = Field(..., min_length=1, max_length=4096)
    scenario_id: str | None = Field(default=None, max_length=128)
    status: CampaignStatus = CampaignStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateBusinessCampaignRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    goal: str | None = Field(default=None, min_length=1, max_length=4096)
    scenario_id: str | None = Field(default=None, max_length=128)
    status: CampaignStatus | None = None
    metadata: dict[str, Any] | None = None


@router.post("", response_model=Campaign, status_code=status.HTTP_201_CREATED)
async def create_business_campaign(
    body: CreateBusinessCampaignRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Campaign:
    service = CampaignLayerService(session)
    try:
        row = await service.create(
            current_user.id,
            project.id,
            name=body.name,
            goal=body.goal,
            scenario_id=body.scenario_id,
            status=body.status,
            metadata=body.metadata,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return campaign_to_contract(row)


@router.get("", response_model=list[Campaign] | list[CampaignControlCenterSummary])
async def list_business_campaigns(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    status_filter: CampaignStatus | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=False),
    view: str | None = Query(default=None, max_length=32),
    health: CampaignHealthStatus | None = Query(default=None),
    next_action_type: CampaignNextActionType | None = Query(default=None),
    failed_only: bool = Query(default=False),
    completed_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[Campaign] | list[CampaignControlCenterSummary]:
    if view == "control":
        control_service = CampaignControlCenterService(session)
        summaries = await control_service.list_summaries(
            current_user.id,
            project.id,
            health=health,
            next_action_type=next_action_type,
            failed_only=failed_only,
            completed_only=completed_only,
            status=status_filter,
            limit=limit,
        )
        if summaries is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return summaries

    service = CampaignLayerService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        status=status_filter,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [campaign_to_contract(row) for row in rows]


@router.get("/search", response_model=list[Campaign] | list[CampaignControlCenterSummary])
async def search_business_campaigns(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    q: str | None = Query(default=None, max_length=256),
    scenario_id: str | None = Query(default=None, max_length=128),
    status_filter: CampaignStatus | None = Query(default=None, alias="status"),
    view: str | None = Query(default=None, max_length=32),
    health: CampaignHealthStatus | None = Query(default=None),
    next_action_type: CampaignNextActionType | None = Query(default=None),
    failed_only: bool = Query(default=False),
    completed_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Campaign] | list[CampaignControlCenterSummary]:
    if view == "control":
        control_service = CampaignControlCenterService(session)
        summaries = await control_service.list_summaries(
            current_user.id,
            project.id,
            query=q,
            scenario_id=scenario_id,
            status=status_filter,
            health=health,
            next_action_type=next_action_type,
            failed_only=failed_only,
            completed_only=completed_only,
            limit=limit,
        )
        if summaries is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return summaries

    service = CampaignLayerService(session)
    rows = await service.search(
        current_user.id,
        project.id,
        query=q,
        scenario_id=scenario_id,
        status=status_filter,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [campaign_to_contract(row) for row in rows]


@router.get("/{campaign_id}", response_model=Campaign)
async def get_business_campaign(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Campaign:
    service = CampaignLayerService(session)
    row = await service.get(current_user.id, project.id, campaign_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    return campaign_to_contract(row)


@router.patch("/{campaign_id}", response_model=Campaign)
async def update_business_campaign(
    campaign_id: UUID,
    body: UpdateBusinessCampaignRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Campaign:
    updates = body.model_dump(exclude_unset=True)
    service = CampaignLayerService(session)
    try:
        row = await service.update(current_user.id, project.id, campaign_id, updates)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    return campaign_to_contract(row)


@router.get("/{campaign_id}/control-center", response_model=CampaignControlCenter)
async def get_business_campaign_control_center(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignControlCenter:
    service = CampaignControlCenterService(session)
    center = await service.get_control_center(current_user.id, project.id, campaign_id)
    if center is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    return center


@router.get("/{campaign_id}/supervisor-report", response_model=CampaignSupervisorReport)
async def get_business_campaign_supervisor_report(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignSupervisorReport:
    report = await CampaignSupervisorService(session).get_report(
        current_user.id,
        project.id,
        campaign_id,
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    return report


@router.get("/{campaign_id}/workflows/templates", response_model=list[CampaignWorkflowTemplate])
async def list_campaign_workflow_templates(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[CampaignWorkflowTemplate]:
    _ = campaign_id, current_user
    return await CampaignWorkflowService(session).list_templates()


@router.post(
    "/{campaign_id}/workflows/{template_id}/create-run",
    response_model=CampaignWorkflowRun,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign_workflow_run(
    campaign_id: UUID,
    template_id: str,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignWorkflowRun:
    service = CampaignWorkflowService(session)
    try:
        run = await service.create_run(
            current_user.id,
            project.id,
            campaign_id,
            template_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    return run


@router.get("/{campaign_id}/dashboard", response_model=CampaignDashboard)
async def get_business_campaign_dashboard(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignDashboard:
    service = CampaignLayerService(session)
    dashboard = await service.get_dashboard(current_user.id, project.id, campaign_id)
    if dashboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    return dashboard


@router.get("/{campaign_id}/metrics", response_model=CampaignMetrics)
async def get_business_campaign_metrics(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignMetrics:
    service = CampaignLayerService(session)
    metrics = await service.compute_metrics(current_user.id, project.id, campaign_id)
    if metrics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    return metrics


@router.post(
    "/{campaign_id}/scenario-wizard-runs",
    response_model=ScenarioWizardRun,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign_scenario_wizard_run(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ScenarioWizardRun:
    campaign_service = CampaignLayerService(session)
    campaign = await campaign_service.get(current_user.id, project.id, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    if not campaign.scenario_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign has no scenario_id — attach a scenario before starting wizard",
        )

    wizard_service = ScenarioWizardService(session)
    try:
        row = await wizard_service.create_run(
            current_user.id,
            project.id,
            campaign.scenario_id,
            source_campaign_id=campaign_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return scenario_wizard_run_to_contract(row)


@router.post(
    "/{campaign_id}/actions/{action_type}/execute",
    response_model=CampaignActionResult,
)
async def execute_campaign_action(
    campaign_id: UUID,
    action_type: CampaignActionType,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CampaignActionResult:
    service = CampaignActionExecutorService(session)
    try:
        result = await service.execute(
            current_user.id,
            project.id,
            campaign_id,
            action_type,
            idempotency_key=idempotency_key,
            include_snapshot=True,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business campaign not found",
        )
    return result
