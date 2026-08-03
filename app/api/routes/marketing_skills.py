"""Marketing skill runs API (Phase AI.234)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.api.mappers import marketing_skill_run_to_contract
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import MarketingSkillDefinition, MarketingSkillRun, MarketingSkillType
from app.services.marketing_skill_run_service import MarketingSkillRunService

router = APIRouter(
    prefix="/projects/{project_id}/marketing-skills",
    tags=["marketing-skills"],
)


class MarketingSkillRunCreateRequest(BaseModel):
    input_payload: dict[str, Any] = Field(default_factory=dict)
    campaign_id: UUID | None = None


def _invalid_state_http(exc: InvalidStateError) -> HTTPException:
    code = str(exc)
    if code == "marketing_skills_disabled":
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Marketing skills are disabled",
        )
    if code == "marketing_skill_forbidden_input_key":
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Input payload contains forbidden secret-like keys",
        )
    if code == "marketing_skill_invalid_input":
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid skill input payload",
        )
    raise exc


@router.get("/definitions", response_model=list[MarketingSkillDefinition])
async def list_marketing_skill_definitions(
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    _user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[MarketingSkillDefinition]:
    _ = project_id
    return MarketingSkillRunService(session).list_skill_definitions()


@router.post(
    "/{skill_type}/runs",
    response_model=MarketingSkillRun,
    status_code=status.HTTP_201_CREATED,
)
async def create_marketing_skill_run(
    skill_type: MarketingSkillType,
    body: MarketingSkillRunCreateRequest,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> MarketingSkillRun:
    service = MarketingSkillRunService(session)
    try:
        row = await service.create_run(
            user.id,
            project_id,
            skill_type,
            body.input_payload,
            campaign_id=body.campaign_id,
        )
    except InvalidStateError as exc:
        raise _invalid_state_http(exc) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return marketing_skill_run_to_contract(row)


@router.get("/runs", response_model=list[MarketingSkillRun])
async def list_marketing_skill_runs(
    project_id: UUID,
    campaign_id: UUID | None = Query(default=None),
    skill_type: MarketingSkillType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[MarketingSkillRun]:
    service = MarketingSkillRunService(session)
    rows = await service.list_runs(
        user.id,
        project_id,
        campaign_id=campaign_id,
        skill_type=skill_type,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [marketing_skill_run_to_contract(row) for row in rows]


@router.get("/runs/{run_id}", response_model=MarketingSkillRun)
async def get_marketing_skill_run(
    run_id: UUID,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> MarketingSkillRun:
    service = MarketingSkillRunService(session)
    row = await service.get_run(user.id, project_id, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill run not found")
    return marketing_skill_run_to_contract(row)
