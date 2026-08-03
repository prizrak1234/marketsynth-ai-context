"""Marketing briefs API (Phase 4.0)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import marketing_brief_to_contract
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.marketing.contracts import MarketingBrief
from app.schemas.marketing import MarketingBriefCreateRequest, MarketingBriefUpdateRequest
from app.services.marketing_brief_service import MarketingBriefService

router = APIRouter(
    prefix="/projects/{project_id}/marketing-briefs",
    tags=["marketing-briefs"],
)


@router.post("", response_model=MarketingBrief, status_code=status.HTTP_201_CREATED)
async def create_marketing_brief(
    body: MarketingBriefCreateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingBrief:
    service = MarketingBriefService(session)
    created = await service.create(
        current_user.id,
        project.id,
        title=body.title,
        product_description=body.product_description,
        target_audience=body.target_audience,
        offer=body.offer,
        goals=body.goals,
        constraints=body.constraints,
    )
    if created is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return marketing_brief_to_contract(created)


@router.get("", response_model=list[MarketingBrief])
async def list_marketing_briefs(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MarketingBrief]:
    service = MarketingBriefService(session)
    rows = await service.list_by_project(
        current_user.id,
        project.id,
        include_archived=include_archived,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [marketing_brief_to_contract(row) for row in rows]


@router.get("/{brief_id}", response_model=MarketingBrief)
async def get_marketing_brief(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingBrief:
    service = MarketingBriefService(session)
    row = await service.get(current_user.id, project.id, brief_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing brief not found",
        )
    return marketing_brief_to_contract(row)


@router.patch("/{brief_id}", response_model=MarketingBrief)
async def update_marketing_brief(
    brief_id: UUID,
    body: MarketingBriefUpdateRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingBrief:
    service = MarketingBriefService(session)
    updated = await service.update(
        current_user.id,
        project.id,
        brief_id,
        body.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing brief not found",
        )
    return marketing_brief_to_contract(updated)


@router.delete("/{brief_id}", response_model=MarketingBrief)
async def archive_marketing_brief(
    brief_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> MarketingBrief:
    service = MarketingBriefService(session)
    archived = await service.archive(current_user.id, project.id, brief_id)
    if archived is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marketing brief not found",
        )
    return marketing_brief_to_contract(archived)
