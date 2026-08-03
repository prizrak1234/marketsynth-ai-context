"""General Business Operator API (Phase AI.180–AI.213)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_project_owner
from app.api.deps import get_session
from app.core.exceptions import InvalidStateError
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.schemas.contracts import (
    BusinessIntent,
    BusinessOperatorAnalyzeResponse,
    BusinessOperatorBriefConfirmResponse,
    BusinessOperatorBriefResponse,
    BusinessOperatorClarifyResponse,
    BusinessOperatorCreateCampaignResponse,
    CampaignBriefFields,
)
from app.services.business_operator_service import BusinessOperatorService

router = APIRouter(
    prefix="/projects/{project_id}/business-operator",
    tags=["business-operator"],
)


class BusinessOperatorMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)


class BusinessOperatorClarifyRequest(BaseModel):
    previous_intent: BusinessIntent
    answers: dict[str, str] = Field(default_factory=dict)


class BusinessOperatorBriefRequest(BaseModel):
    intent: BusinessIntent
    recommended_scenario: str = Field(..., min_length=1, max_length=128)
    brief: CampaignBriefFields
    answers: dict[str, str] = Field(default_factory=dict)


class BusinessOperatorBriefConfirmRequest(BaseModel):
    intent: BusinessIntent
    recommended_scenario: str = Field(..., min_length=1, max_length=128)
    brief: CampaignBriefFields


class BusinessOperatorCreateCampaignRequest(BaseModel):
    message: str | None = Field(default=None, min_length=1, max_length=4096)
    intent: BusinessIntent | None = None
    brief_id: UUID

    @model_validator(mode="after")
    def require_message_or_intent(self) -> BusinessOperatorCreateCampaignRequest:
        if not self.message and self.intent is None:
            raise ValueError("message or intent is required")
        return self


def _invalid_state_http(exc: InvalidStateError) -> HTTPException:
    code = str(exc)
    if code == "business_operator_confidence_gate":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confidence gate not passed — clarify intent before creating campaign",
        )
    if code == "campaign_brief_completeness_gate":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Brief completeness gate not passed — complete and confirm brief first",
        )
    if code == "campaign_brief_not_confirmed":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirmed campaign brief is required before creating campaign",
        )
    raise exc


@router.post("/analyze", response_model=BusinessOperatorAnalyzeResponse)
async def analyze_business_intent(
    body: BusinessOperatorMessageRequest,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> BusinessOperatorAnalyzeResponse:
    service = BusinessOperatorService(session)
    try:
        result = await service.analyze(user.id, project_id, message=body.message)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return result


@router.post("/clarify", response_model=BusinessOperatorClarifyResponse)
async def clarify_business_intent(
    body: BusinessOperatorClarifyRequest,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> BusinessOperatorClarifyResponse:
    service = BusinessOperatorService(session)
    try:
        result = await service.clarify(
            user.id,
            project_id,
            previous_intent=body.previous_intent,
            answers=body.answers,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return result


@router.post("/brief/complete", response_model=BusinessOperatorBriefResponse)
async def complete_business_brief(
    body: BusinessOperatorBriefRequest,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> BusinessOperatorBriefResponse:
    service = BusinessOperatorService(session)
    result = await service.complete_brief(
        user.id,
        project_id,
        intent=body.intent,
        recommended_scenario=body.recommended_scenario,
        brief=body.brief,
        answers=body.answers,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return result


@router.post("/brief/confirm", response_model=BusinessOperatorBriefConfirmResponse)
async def confirm_business_brief(
    body: BusinessOperatorBriefConfirmRequest,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> BusinessOperatorBriefConfirmResponse:
    service = BusinessOperatorService(session)
    try:
        result = await service.confirm_brief(
            user.id,
            project_id,
            intent=body.intent,
            recommended_scenario=body.recommended_scenario,
            brief=body.brief,
        )
    except InvalidStateError as exc:
        raise _invalid_state_http(exc) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return result


@router.post(
    "/create-campaign",
    response_model=BusinessOperatorCreateCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign_from_operator(
    body: BusinessOperatorCreateCampaignRequest,
    project_id: UUID,
    _project: ProjectTable = Depends(require_project_owner),
    user: UserTable = Depends(require_active_user),
    session: AsyncSession = Depends(get_session),
) -> BusinessOperatorCreateCampaignResponse:
    service = BusinessOperatorService(session)
    try:
        result = await service.create_campaign(
            user.id,
            project_id,
            message=body.message,
            intent=body.intent,
            brief_id=body.brief_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except InvalidStateError as exc:
        raise _invalid_state_http(exc) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return result
