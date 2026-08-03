"""E2E demo flow status API (Phase AI.81)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_project_owner
from app.api.dependencies.demo_flow import require_demo_flow_access
from app.api.deps import get_session
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.demo.provenance_helpers import build_content_production_provenance
from app.api.dependencies.demo_flow_reset import require_demo_flow_reset_access
from app.schemas.demo_flow import (
    ContentProductionProvenanceResponse,
    DemoFlowResetResponse,
    DemoFlowStatusResponse,
)
from app.services.demo_flow_status_service import DemoFlowStatusService
from app.services.e2e_demo_reset_service import E2eDemoResetService

demo_flow_router = APIRouter(
    prefix="/projects/{project_id}/demo-flow",
    tags=["demo-flow"],
)

provenance_router = APIRouter(
    prefix="/projects/{project_id}/provenance/content-production",
    tags=["provenance"],
)


@demo_flow_router.get("/status", response_model=DemoFlowStatusResponse)
async def get_demo_flow_status(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_demo_flow_access),
) -> DemoFlowStatusResponse:
    service = DemoFlowStatusService(session)
    result = await service.get_status(current_user.id, project.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return result


@demo_flow_router.post("/reset", response_model=DemoFlowResetResponse)
async def reset_demo_flow(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_demo_flow_reset_access),
) -> DemoFlowResetResponse:
    result = await E2eDemoResetService(session).reset_project(current_user.id, project.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return DemoFlowResetResponse(
        project_id=result.project_id,
        cleared=result.cleared,
        removed_counts=result.removed_counts,
    )


@provenance_router.get(
    "/{publication_job_id}",
    response_model=ContentProductionProvenanceResponse,
)
async def get_content_production_provenance(
    publication_job_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_demo_flow_access),
) -> ContentProductionProvenanceResponse:
    result = await build_content_production_provenance(
        session,
        current_user.id,
        project.id,
        publication_job_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication package job not found",
        )
    return result
