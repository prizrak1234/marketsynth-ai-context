"""Product Skill Runtime API — PROGRAM-CONTENT-01-SKILL-RUNTIME-01."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.product_skills.runtime_service import ProductSkillRuntimeService
from app.schemas.contracts import (
    ProductSkillIndexItem,
    ProductSkillRunCreate,
    ProductSkillRunRead,
    ProductSkillWorkspaceState,
)

router = APIRouter(tags=["product-skills"])


@router.get("/skills", response_model=list[ProductSkillIndexItem])
async def list_product_skills(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[ProductSkillIndexItem]:
    service = ProductSkillRuntimeService(session)
    return await service.list_skills(current_user.id)


@router.get("/skills/workspace", response_model=ProductSkillWorkspaceState)
async def product_skills_workspace(
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ProductSkillWorkspaceState:
    service = ProductSkillRuntimeService(session)
    return await service.workspace(current_user.id)


@router.post(
    "/projects/{project_id}/skills/runs",
    response_model=ProductSkillRunRead,
)
async def execute_product_skill(
    body: ProductSkillRunCreate,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ProductSkillRunRead:
    service = ProductSkillRuntimeService(session)
    try:
        run = await service.execute(current_user.id, project.id, body)
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return run


@router.get(
    "/projects/{project_id}/skills/runs/{run_id}",
    response_model=ProductSkillRunRead,
)
async def get_product_skill_run(
    run_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ProductSkillRunRead:
    service = ProductSkillRuntimeService(session)
    run = await service.get_run(current_user.id, project.id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return run
