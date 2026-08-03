"""Marketing funnels API (Phase 4.8)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    funnel_step_asset_link_to_contract,
    funnel_step_linked_asset_to_contract,
    marketing_funnel_step_to_contract,
    marketing_funnel_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.marketing.funnel_contracts import (
    FunnelStepAssetLink,
    FunnelStepLinkedAsset,
    MarketingFunnel,
    MarketingFunnelStep,
)
from app.schemas.marketing_funnels import (
    FunnelStepAssetLinkCreateRequest,
    MarketingFunnelCreateRequest,
    MarketingFunnelStepCreateRequest,
    MarketingFunnelStepReorderRequest,
    MarketingFunnelStepUpdateRequest,
    MarketingFunnelUpdateRequest,
)
from app.services.marketing_funnel_service import MarketingFunnelService

router = APIRouter(
    prefix="/projects/{project_id}/funnels",
    tags=["marketing-funnels"],
)


@router.post("", response_model=MarketingFunnel, status_code=status.HTTP_201_CREATED)
async def create_funnel(
    body: MarketingFunnelCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingFunnel:
    service = MarketingFunnelService(session)
    created = await service.create_funnel(
        current_user.id,
        project.id,
        title=body.title,
        description=body.description,
        brief_id=body.brief_id,
        metadata=body.metadata,
    )
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or brief not found",
        )
    return marketing_funnel_to_contract(created)


@router.get("", response_model=list[MarketingFunnel])
async def list_funnels(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MarketingFunnel]:
    service = MarketingFunnelService(session)
    rows = await service.list_funnels(
        current_user.id,
        project.id,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [marketing_funnel_to_contract(row) for row in rows]


@router.get("/{funnel_id}", response_model=MarketingFunnel)
async def get_funnel(
    funnel_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingFunnel:
    service = MarketingFunnelService(session)
    row = await service.get_funnel(current_user.id, project.id, funnel_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel not found")
    return marketing_funnel_to_contract(row)


@router.patch("/{funnel_id}", response_model=MarketingFunnel)
async def update_funnel(
    funnel_id: UUID,
    body: MarketingFunnelUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingFunnel:
    service = MarketingFunnelService(session)
    updated = await service.update_funnel(
        current_user.id,
        project.id,
        funnel_id,
        body.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel, project, or brief not found",
        )
    return marketing_funnel_to_contract(updated)


@router.delete("/{funnel_id}", response_model=MarketingFunnel)
async def archive_funnel(
    funnel_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingFunnel:
    service = MarketingFunnelService(session)
    try:
        archived = await service.archive_funnel(current_user.id, project.id, funnel_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if archived is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel not found")
    return marketing_funnel_to_contract(archived)


@router.post(
    "/{funnel_id}/steps",
    response_model=MarketingFunnelStep,
    status_code=status.HTTP_201_CREATED,
)
async def create_funnel_step(
    funnel_id: UUID,
    body: MarketingFunnelStepCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingFunnelStep:
    service = MarketingFunnelService(session)
    try:
        created = await service.create_step(
            current_user.id,
            project.id,
            funnel_id,
            step_type=body.step_type,
            title=body.title,
            description=body.description,
            position=body.position,
            metadata=body.metadata,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if created is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel not found")
    return marketing_funnel_step_to_contract(created)


@router.get("/{funnel_id}/steps", response_model=list[MarketingFunnelStep])
async def list_funnel_steps(
    funnel_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_archived: bool = Query(default=False),
) -> list[MarketingFunnelStep]:
    service = MarketingFunnelService(session)
    rows = await service.list_steps(
        current_user.id,
        project.id,
        funnel_id,
        include_archived=include_archived,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel not found")
    return [marketing_funnel_step_to_contract(row) for row in rows]


@router.post("/{funnel_id}/steps/reorder", response_model=list[MarketingFunnelStep])
async def reorder_funnel_steps(
    funnel_id: UUID,
    body: MarketingFunnelStepReorderRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[MarketingFunnelStep]:
    service = MarketingFunnelService(session)
    try:
        rows = await service.reorder_steps(
            current_user.id,
            project.id,
            funnel_id,
            body.step_ids,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel not found")
    return [marketing_funnel_step_to_contract(row) for row in rows]


@router.patch("/{funnel_id}/steps/{step_id}", response_model=MarketingFunnelStep)
async def update_funnel_step(
    funnel_id: UUID,
    step_id: UUID,
    body: MarketingFunnelStepUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingFunnelStep:
    service = MarketingFunnelService(session)
    try:
        updated = await service.update_step(
            current_user.id,
            project.id,
            funnel_id,
            step_id,
            body.model_dump(exclude_unset=True),
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel step not found")
    return marketing_funnel_step_to_contract(updated)


@router.delete("/{funnel_id}/steps/{step_id}", response_model=MarketingFunnelStep)
async def archive_funnel_step(
    funnel_id: UUID,
    step_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingFunnelStep:
    service = MarketingFunnelService(session)
    try:
        archived = await service.archive_step(
            current_user.id,
            project.id,
            funnel_id,
            step_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if archived is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel step not found")
    return marketing_funnel_step_to_contract(archived)


@router.post(
    "/{funnel_id}/steps/{step_id}/assets",
    response_model=FunnelStepAssetLink,
    status_code=status.HTTP_201_CREATED,
)
async def link_asset_to_funnel_step(
    funnel_id: UUID,
    step_id: UUID,
    body: FunnelStepAssetLinkCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> FunnelStepAssetLink:
    service = MarketingFunnelService(session)
    try:
        linked = await service.link_asset_to_step(
            current_user.id,
            project.id,
            funnel_id,
            step_id,
            body.asset_id,
            role=body.role,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if linked is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funnel, step, or asset not found",
        )
    return funnel_step_asset_link_to_contract(linked)


@router.get("/{funnel_id}/steps/{step_id}/assets", response_model=list[FunnelStepLinkedAsset])
async def list_funnel_step_assets(
    funnel_id: UUID,
    step_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[FunnelStepLinkedAsset]:
    service = MarketingFunnelService(session)
    rows = await service.list_step_assets(
        current_user.id,
        project.id,
        funnel_id,
        step_id,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel step not found")
    return [funnel_step_linked_asset_to_contract(row) for row in rows]


@router.delete(
    "/{funnel_id}/steps/{step_id}/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_asset_from_funnel_step(
    funnel_id: UUID,
    step_id: UUID,
    asset_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> Response:
    service = MarketingFunnelService(session)
    removed = await service.unlink_asset_from_step(
        current_user.id,
        project.id,
        funnel_id,
        step_id,
        asset_id,
    )
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset link not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
