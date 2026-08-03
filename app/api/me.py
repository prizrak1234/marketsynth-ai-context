"""Current-user API routes."""



from __future__ import annotations



from uuid import UUID



from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.ext.asyncio import AsyncSession



from app.api.dependencies.auth import require_active_user, require_active_user_unrestricted

from app.api.dependencies.beta_admin import require_beta_admin_access

from app.api.deps import get_session

from app.api.mappers import beta_feedback_report_to_contract, user_to_contract

from app.core.exceptions import InvalidStateError, NotFoundError

from app.db.models.user import UserTable

from app.schemas.beta_access import BetaAccessResponse, BetaAdminUserAccessRequest
from app.schemas.beta_admin import BetaAdminDashboardResponse, BetaQaExportResponse
from app.schemas.beta_feedback import BetaFeedbackAdminFilters, BetaFeedbackCreateRequest
from app.schemas.beta_guide import BetaGuideResponse
from app.schemas.contracts import BetaFeedbackReport, BetaFeedbackStatus, User, UserRole

from app.schemas.onboarding import (

    OnboardingCompleteStepRequest,

    OnboardingStatusResponse,

)

from app.schemas.operational_metrics import OperationalMetricsResponse

from app.services.beta_access_service import BetaAccessService
from app.services.beta_admin_service import BetaAdminService
from app.services.beta_feedback_service import BetaFeedbackService
from app.services.beta_guide_service import BetaGuideService

from app.services.onboarding_service import OnboardingService

from app.services.operational_metrics_service import OperationalMetricsService



router = APIRouter(prefix="/me", tags=["me"])


@router.get("/beta-access", response_model=BetaAccessResponse)
async def get_my_beta_access(
    current_user: UserTable = Depends(require_active_user_unrestricted),
) -> BetaAccessResponse:
    return BetaAccessService.status_response(current_user)


@router.get("/beta-guide", response_model=BetaGuideResponse)
async def get_my_beta_guide(
    current_user: UserTable = Depends(require_active_user_unrestricted),
) -> BetaGuideResponse:
    del current_user
    return BetaGuideService.get_guide()



@router.get("/operational-metrics", response_model=OperationalMetricsResponse)

async def get_my_operational_metrics(

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_active_user),

) -> OperationalMetricsResponse:

    service = OperationalMetricsService(session)

    return await service.get_owner_operational_metrics(current_user.id)





@router.get("/onboarding", response_model=OnboardingStatusResponse)

async def get_my_onboarding(

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_active_user),

    project_id: UUID | None = Query(default=None),

) -> OnboardingStatusResponse:

    result = await OnboardingService(session).get_status(

        current_user.id,

        project_id=project_id,

    )

    if result is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return result





@router.post("/onboarding/complete-step", response_model=OnboardingStatusResponse)

async def complete_onboarding_step(

    body: OnboardingCompleteStepRequest,

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_active_user),

) -> OnboardingStatusResponse:

    try:

        result = await OnboardingService(session).complete_manual_step(

            current_user.id,

            body.step,

        )

    except InvalidStateError as exc:

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if result is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return result





@router.post("/beta-feedback", response_model=BetaFeedbackReport, status_code=status.HTTP_201_CREATED)

async def create_beta_feedback(

    body: BetaFeedbackCreateRequest,

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_active_user_unrestricted),

) -> BetaFeedbackReport:

    try:

        row = await BetaFeedbackService(session).create(current_user.id, body)

    except InvalidStateError as exc:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return beta_feedback_report_to_contract(row)





@router.get("/beta-feedback", response_model=list[BetaFeedbackReport])

async def list_my_beta_feedback(

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_active_user_unrestricted),

    status_filter: BetaFeedbackStatus | None = Query(default=None, alias="status"),

    limit: int = Query(default=100, ge=1, le=200),

) -> list[BetaFeedbackReport]:

    rows = await BetaFeedbackService(session).list_for_owner(

        current_user.id,

        status=status_filter,

        limit=limit,

    )

    return [beta_feedback_report_to_contract(row) for row in rows]





@router.get("/beta-feedback/{report_id}", response_model=BetaFeedbackReport)

async def get_my_beta_feedback(

    report_id: UUID,

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_active_user_unrestricted),

) -> BetaFeedbackReport:

    row = await BetaFeedbackService(session).get_for_owner(current_user.id, report_id)

    if row is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    return beta_feedback_report_to_contract(row)





@router.post("/beta-feedback/{report_id}/archive", response_model=BetaFeedbackReport)

async def archive_my_beta_feedback(

    report_id: UUID,

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_active_user_unrestricted),

) -> BetaFeedbackReport:

    row = await BetaFeedbackService(session).archive(current_user.id, report_id)

    if row is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    return beta_feedback_report_to_contract(row)





@router.get("/beta-admin/dashboard", response_model=BetaAdminDashboardResponse)

async def get_beta_admin_dashboard(

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_beta_admin_access),

) -> BetaAdminDashboardResponse:

    scoped_owner: UUID | None = current_user.id

    if current_user.role == UserRole.ADMIN:

        scoped_owner = None

    return await BetaAdminService(session).get_dashboard(scoped_owner_id=scoped_owner)





@router.get("/beta-admin/feedback", response_model=list[BetaFeedbackReport])

async def list_beta_admin_feedback(

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_beta_admin_access),

    filters: BetaFeedbackAdminFilters = Depends(),

) -> list[BetaFeedbackReport]:

    scoped_owner: UUID | None = current_user.id

    if current_user.role == UserRole.ADMIN:

        scoped_owner = None

    rows = await BetaFeedbackService(session).list_admin(

        owner_id=scoped_owner,

        project_id=filters.project_id,

        source=filters.source,

        severity=filters.severity,

        status=filters.status,

        date_from=filters.date_from,

        date_to=filters.date_to,

        limit=filters.limit,

    )

    return [beta_feedback_report_to_contract(row) for row in rows]





@router.post("/beta-admin/feedback/{report_id}/triage", response_model=BetaFeedbackReport)

async def triage_beta_admin_feedback(

    report_id: UUID,

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_beta_admin_access),

) -> BetaFeedbackReport:

    del current_user

    try:

        row = await BetaFeedbackService(session).triage(report_id)

    except InvalidStateError as exc:

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if row is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    return beta_feedback_report_to_contract(row)





@router.post("/beta-admin/feedback/{report_id}/resolve", response_model=BetaFeedbackReport)

async def resolve_beta_admin_feedback(

    report_id: UUID,

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_beta_admin_access),

) -> BetaFeedbackReport:

    del current_user

    try:

        row = await BetaFeedbackService(session).resolve(report_id)

    except InvalidStateError as exc:

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if row is None:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    return beta_feedback_report_to_contract(row)





@router.get("/beta-admin/qa-export", response_model=BetaQaExportResponse)

async def get_beta_admin_qa_export(

    session: AsyncSession = Depends(get_session),

    current_user: UserTable = Depends(require_beta_admin_access),

) -> BetaQaExportResponse:

    scoped_owner: UUID | None = current_user.id

    if current_user.role == UserRole.ADMIN:

        scoped_owner = None

    return await BetaAdminService(session).get_qa_export(scoped_owner_id=scoped_owner)


@router.post("/beta-admin/users/{user_id}/approve-beta", response_model=User)
async def approve_beta_access(
    user_id: UUID,
    body: BetaAdminUserAccessRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_beta_admin_access),
) -> User:
    del current_user
    try:
        row = await BetaAccessService(session).approve(
            user_id,
            notes=body.notes if body else None,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return user_to_contract(row)


@router.post("/beta-admin/users/{user_id}/block-beta", response_model=User)
async def block_beta_access(
    user_id: UUID,
    body: BetaAdminUserAccessRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_beta_admin_access),
) -> User:
    del current_user
    try:
        row = await BetaAccessService(session).block(
            user_id,
            notes=body.notes if body else None,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return user_to_contract(row)

