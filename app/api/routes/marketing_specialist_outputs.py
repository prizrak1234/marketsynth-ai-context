"""Marketing specialist output API (Phase AI.30)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import (
    marketing_specialist_output_to_contract,
    marketing_specialist_output_version_to_contract,
)
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    CreateContentAssetFromCopywriterResponse,
    MarketingSpecialistOutput,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistOutputVersion,
    MarketingSpecialistType,
)
from app.services.marketing_specialist_output_service import MarketingSpecialistOutputService

router = APIRouter(
    prefix="/projects/{project_id}/marketing-specialist-outputs",
    tags=["marketing-specialist-outputs"],
)


@router.get("", response_model=list[MarketingSpecialistOutput])
async def list_marketing_specialist_outputs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    execution_run_id: UUID | None = None,
    marketing_plan_id: UUID | None = None,
    specialist: MarketingSpecialistType | None = None,
    status_filter: MarketingSpecialistOutputStatus | None = Query(
        default=None,
        alias="status",
    ),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[MarketingSpecialistOutput]:
    service = MarketingSpecialistOutputService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        execution_run_id=execution_run_id,
        marketing_plan_id=marketing_plan_id,
        specialist=specialist,
        status=status_filter,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [marketing_specialist_output_to_contract(row) for row in rows]


@router.get("/{output_id}", response_model=MarketingSpecialistOutput)
async def get_marketing_specialist_output(
    output_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingSpecialistOutput:
    service = MarketingSpecialistOutputService(session)
    row = await service.get(current_user.id, project.id, output_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing specialist output not found",
        )
    return marketing_specialist_output_to_contract(row)


@router.post("/{output_id}/approve", response_model=MarketingSpecialistOutput)
async def approve_marketing_specialist_output(
    output_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingSpecialistOutput:
    service = MarketingSpecialistOutputService(session)
    try:
        row = await service.approve(current_user.id, project.id, output_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing specialist output not found",
        )
    return marketing_specialist_output_to_contract(row)


@router.post(
    "/{output_id}/create-content-asset",
    response_model=CreateContentAssetFromCopywriterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_asset_from_copywriter_output(
    output_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> CreateContentAssetFromCopywriterResponse:
    service = MarketingSpecialistOutputService(session)
    try:
        asset = await service.create_content_asset_from_copywriter(
            current_user.id,
            project.id,
            output_id,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing specialist output not found",
        )
    return CreateContentAssetFromCopywriterResponse(
        specialist_output_id=output_id,
        content_asset_id=asset.id,
        content_asset_status=asset.status.value
        if hasattr(asset.status, "value")
        else str(asset.status),
    )


@router.post("/{output_id}/archive", response_model=MarketingSpecialistOutput)
async def archive_marketing_specialist_output(
    output_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingSpecialistOutput:
    service = MarketingSpecialistOutputService(session)
    try:
        row = await service.archive(current_user.id, project.id, output_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing specialist output not found",
        )
    return marketing_specialist_output_to_contract(row)


@router.get("/{output_id}/versions", response_model=list[MarketingSpecialistOutputVersion])
async def list_marketing_specialist_output_versions(
    output_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[MarketingSpecialistOutputVersion]:
    service = MarketingSpecialistOutputService(session)
    rows = await service.list_versions(current_user.id, project.id, output_id)
    if rows is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing specialist output not found",
        )
    return [marketing_specialist_output_version_to_contract(row) for row in rows]


@router.get(
    "/{output_id}/versions/{version_number}",
    response_model=MarketingSpecialistOutputVersion,
)
async def get_marketing_specialist_output_version(
    output_id: UUID,
    version_number: int,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingSpecialistOutputVersion:
    if version_number < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="version_number must be >= 1",
        )
    service = MarketingSpecialistOutputService(session)
    row = await service.get_version(
        current_user.id,
        project.id,
        output_id,
        version_number,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing specialist output version not found",
        )
    return marketing_specialist_output_version_to_contract(row)
