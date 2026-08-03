"""Content Factory commercial copywriter generation API (R3.3B-LITE)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_text
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    ContentFactoryGenerateMaterialsRequest,
    ContentFactoryGenerateMaterialsResponse,
    ContentFactoryProviderReadiness,
)
from app.services.content_factory_generation_service import ContentFactoryGenerationService

router = APIRouter(
    prefix="/projects/{project_id}/content-factory",
    tags=["content-factory"],
)


@router.get("/provider-readiness", response_model=ContentFactoryProviderReadiness)
async def get_content_factory_provider_readiness(
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentFactoryProviderReadiness:
    _ = project, current_user
    service = ContentFactoryGenerationService(session)
    return await service.provider_readiness()


@router.post("/generate-materials", response_model=ContentFactoryGenerateMaterialsResponse)
async def generate_content_factory_materials(
    body: ContentFactoryGenerateMaterialsRequest,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentFactoryGenerateMaterialsResponse:
    service = ContentFactoryGenerationService(session)
    brief = body.brief.model_copy(
        update={
            "topic": sanitize_text(body.brief.topic),
            "goal": sanitize_text(body.brief.goal),
            "audience": sanitize_text(body.brief.audience),
            "channel": sanitize_text(body.brief.channel),
            "period": sanitize_text(body.brief.period),
            "frequency": sanitize_text(body.brief.frequency),
            "format": sanitize_text(body.brief.format),
            "tone_brand_constraints": sanitize_text(body.brief.tone_brand_constraints),
            "source_materials": sanitize_text(body.brief.source_materials),
        },
    )
    try:
        return await service.generate_materials(
            current_user.id,
            project.id,
            brief=brief,
            execution_run_id=body.execution_run_id,
            step=body.step,
            idempotency_key=body.idempotency_key,
        )
    except InvalidStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/generation-runs/{execution_run_id}/status",
    response_model=ContentFactoryGenerateMaterialsResponse,
)
async def get_content_factory_generation_status(
    execution_run_id: UUID,
    project: ProjectTable = Depends(require_project_owner),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> ContentFactoryGenerateMaterialsResponse:
    service = ContentFactoryGenerationService(session)
    result = await service.get_generation_status(
        current_user.id,
        project.id,
        execution_run_id,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation run not found")
    return result
