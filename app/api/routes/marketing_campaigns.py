"""Marketing campaigns API (Phase 9.0)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    campaign_plan_draft_to_contract,
    marketing_campaign_to_contract,
    publication_job_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.db.repositories.publication_jobs import PublicationJobRepository
from app.marketing.contracts import CampaignPlanDraft, MarketingCampaign
from app.publishing.contracts import PublicationJob
from app.schemas.campaign_plan_drafts import (
    CampaignPlanDraftCreateRequest,
    PlanDraftGenerateAssetsResponse,
)
from app.schemas.marketing_campaigns import (
    CampaignAssetListItem,
    CampaignOverviewResponse,
    CampaignWorkflowResponse,
    MarketingCampaignCreateRequest,
    MarketingCampaignUpdateRequest,
)
from app.services.campaign_overview_service import CampaignOverviewService
from app.services.campaign_workflow_service import CampaignWorkflowService
from app.services.campaign_plan_draft_service import CampaignPlanDraftService
from app.services.content_asset_service import ContentAssetService
from app.services.marketing_campaign_service import MarketingCampaignService

router = APIRouter(
    prefix="/projects/{project_id}/campaigns",
    tags=["marketing-campaigns"],
)


@router.post("", response_model=MarketingCampaign, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: MarketingCampaignCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingCampaign:
    service = MarketingCampaignService(session)
    try:
        created = await service.create(
            current_user.id,
            project.id,
            brief_id=body.brief_id,
            title=body.title,
            description=body.description,
            status=body.status,
            start_at=body.start_at,
            end_at=body.end_at,
            campaign_metadata=body.campaign_metadata,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or brief not found",
        )
    return marketing_campaign_to_contract(created)


@router.get("", response_model=list[MarketingCampaign])
async def list_campaigns(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MarketingCampaign]:
    service = MarketingCampaignService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [marketing_campaign_to_contract(row) for row in rows]


@router.get("/{campaign_id}", response_model=MarketingCampaign)
async def get_campaign(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingCampaign:
    service = MarketingCampaignService(session)
    row = await service.get(current_user.id, project.id, campaign_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return marketing_campaign_to_contract(row)


@router.patch("/{campaign_id}", response_model=MarketingCampaign)
async def update_campaign(
    campaign_id: UUID,
    body: MarketingCampaignUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingCampaign:
    service = MarketingCampaignService(session)
    try:
        updated = await service.update(
            current_user.id,
            project.id,
            campaign_id,
            body.model_dump(exclude_unset=True),
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return marketing_campaign_to_contract(updated)


@router.post("/{campaign_id}/archive", response_model=MarketingCampaign)
async def archive_campaign(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingCampaign:
    service = MarketingCampaignService(session)
    try:
        archived = await service.archive(current_user.id, project.id, campaign_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if archived is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return marketing_campaign_to_contract(archived)


@router.get("/{campaign_id}/assets", response_model=list[CampaignAssetListItem])
async def list_campaign_assets(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CampaignAssetListItem]:
    service = MarketingCampaignService(session)
    campaign = await service.get(current_user.id, project.id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    assets = ContentAssetService(session)
    rows = await assets.list_by_campaign(
        current_user.id,
        project.id,
        campaign_id,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return [
        CampaignAssetListItem(
            id=row.id,
            owner_id=row.owner_id,
            project_id=row.project_id,
            brief_id=row.brief_id,
            campaign_id=getattr(row, "campaign_id", None),
            type=str(getattr(row.asset_type, "value", row.asset_type)),
            title=row.title,
            status=str(getattr(row.status, "value", row.status)),
            current_version_number=row.current_version_number,
            approved_version_number=row.approved_version_number,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/{campaign_id}/publication-jobs", response_model=list[PublicationJob])
async def list_campaign_publication_jobs(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PublicationJob]:
    service = MarketingCampaignService(session)
    campaign = await service.get(current_user.id, project.id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    repo = PublicationJobRepository(session)
    rows = await repo.list_by_campaign(
        owner_id=current_user.id,
        project_id=project.id,
        campaign_id=campaign_id,
        limit=limit,
    )
    return [publication_job_to_contract(row) for row in rows]


@router.get("/{campaign_id}/workflow", response_model=CampaignWorkflowResponse)
async def get_campaign_workflow(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignWorkflowResponse:
    service = CampaignWorkflowService(session)
    workflow = await service.get_workflow(
        current_user.id,
        project.id,
        campaign_id,
    )
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return workflow


@router.get("/{campaign_id}/overview", response_model=CampaignOverviewResponse)
async def get_campaign_overview(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignOverviewResponse:
    overview = CampaignOverviewService(session)
    result = await overview.get_overview(
        owner_id=current_user.id,
        project_id=project.id,
        campaign_id=campaign_id,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return result


@router.post(
    "/{campaign_id}/plan-drafts",
    response_model=CampaignPlanDraft,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign_plan_draft(
    campaign_id: UUID,
    body: CampaignPlanDraftCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignPlanDraft:
    service = CampaignPlanDraftService(session)
    try:
        created = await service.create(
            current_user.id,
            project.id,
            campaign_id,
            title=body.title,
            plan_payload=body.plan_payload,
            source_agent_run_id=body.source_agent_run_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project, campaign, or agent run not found",
        )
    return campaign_plan_draft_to_contract(created)


@router.get("/{campaign_id}/plan-drafts", response_model=list[CampaignPlanDraft])
async def list_campaign_plan_drafts(
    campaign_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CampaignPlanDraft]:
    service = CampaignPlanDraftService(session)
    rows = await service.list_by_campaign(
        current_user.id,
        project.id,
        campaign_id,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return [campaign_plan_draft_to_contract(row) for row in rows]


@router.get("/{campaign_id}/plan-drafts/{draft_id}", response_model=CampaignPlanDraft)
async def get_campaign_plan_draft(
    campaign_id: UUID,
    draft_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignPlanDraft:
    service = CampaignPlanDraftService(session)
    row = await service.get(current_user.id, project.id, campaign_id, draft_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign plan draft not found",
        )
    return campaign_plan_draft_to_contract(row)


@router.post("/{campaign_id}/plan-drafts/{draft_id}/archive", response_model=CampaignPlanDraft)
async def archive_campaign_plan_draft(
    campaign_id: UUID,
    draft_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CampaignPlanDraft:
    service = CampaignPlanDraftService(session)
    try:
        archived = await service.archive(
            current_user.id,
            project.id,
            campaign_id,
            draft_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if archived is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign plan draft not found",
        )
    return campaign_plan_draft_to_contract(archived)


@router.post(
    "/{campaign_id}/plan-drafts/{draft_id}/generate-assets",
    response_model=PlanDraftGenerateAssetsResponse,
)
async def generate_assets_from_campaign_plan_draft(
    campaign_id: UUID,
    draft_id: UUID,
    response: Response,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> PlanDraftGenerateAssetsResponse:
    service = CampaignPlanDraftService(session)
    try:
        result = await service.generate_assets(
            current_user.id,
            project.id,
            campaign_id,
            draft_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign plan draft not found",
        )
    response.status_code = (
        status.HTTP_200_OK if result.already_generated else status.HTTP_201_CREATED
    )
    return PlanDraftGenerateAssetsResponse(
        created_count=result.created_count,
        asset_ids=result.asset_ids,
        already_generated=result.already_generated,
    )

