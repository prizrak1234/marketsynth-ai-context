"""CMVP.1 — Business Idea Validation API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user
from app.api.deps import get_session
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.db.models.user import UserTable
from app.db.repositories.mcp_tool_call_audits import McpToolCallAuditRepository
from app.mcp.client import McpClient
from app.schemas.contracts import (
    BivRunObservability,
    BivRunProgress,
    BusinessIdeaValidationAsyncRunAcceptedResponse,
    BusinessIdeaValidationProjectHydration,
    BusinessIdeaValidationProjectLatestRunSummary,
    BusinessIdeaValidationRunRequest,
    BusinessIdeaValidationRunResponse,
    McpToolCallAuditRecord,
)
from app.services.business_idea_validation_service import BusinessIdeaValidationService

router = APIRouter(
    prefix="/user-requests/{user_request_id}/business-idea-validation",
    tags=["business-idea-validation"],
)

project_router = APIRouter(
    prefix="/projects/{project_id}/business-idea-validation",
    tags=["business-idea-validation"],
)


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    code = str(exc)
    status_code = status.HTTP_409_CONFLICT
    if code in {"idempotency_key_required", "idea_too_short", "analysis_context_incomplete"}:
        status_code = status.HTTP_400_BAD_REQUEST
    if code in {
        "analysis_context_required",
        "hydrated_context_confirmation_required",
        "analysis_context_stale",
        "invalid_analysis_context_state",
        "research_idempotency_key_required",
        "rerun_idempotency_key_required",
    }:
        status_code = status.HTTP_409_CONFLICT
    if code in {"mcp_disabled", "not_configured", "business_idea_validation_disabled"}:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HTTPException(status_code=status_code, detail=code)


@router.post(
    "/runs",
    response_model=BusinessIdeaValidationAsyncRunAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def business_idea_validation_enqueue_run(
    user_request_id: UUID,
    body: BusinessIdeaValidationRunRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessIdeaValidationAsyncRunAcceptedResponse:
    svc = BusinessIdeaValidationService(session, settings)
    key = body.idempotency_key or idempotency_key or ""
    payload = body.model_copy(update={"idempotency_key": key})
    try:
        return await svc.enqueue_run(current_user.id, user_request_id, payload)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc


@router.get("/runs/{run_id}", response_model=BusinessIdeaValidationRunResponse)
async def business_idea_validation_get_run(
    user_request_id: UUID,
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessIdeaValidationRunResponse:
    svc = BusinessIdeaValidationService(session, settings)
    try:
        return await svc.get_run_for_owner(current_user.id, user_request_id, run_id)
    except NotFoundError as exc:
        raise _map_error(exc) from exc


@router.get("/runs/{run_id}/progress", response_model=BivRunProgress)
async def business_idea_validation_get_run_progress(
    user_request_id: UUID,
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BivRunProgress:
    svc = BusinessIdeaValidationService(session, settings)
    try:
        return await svc.get_progress_for_run(current_user.id, user_request_id, run_id)
    except NotFoundError as exc:
        raise _map_error(exc) from exc


@router.post("/run", response_model=BusinessIdeaValidationRunResponse)
async def business_idea_validation_run(
    user_request_id: UUID,
    body: BusinessIdeaValidationRunRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessIdeaValidationRunResponse:
    svc = BusinessIdeaValidationService(session, settings)
    key = body.idempotency_key or idempotency_key or ""
    payload = body.model_copy(update={"idempotency_key": key})
    try:
        return await svc.run(current_user.id, user_request_id, payload)
    except (InvalidStateError, NotFoundError) as exc:
        raise _map_error(exc) from exc


@router.get("", response_model=BusinessIdeaValidationRunResponse)
async def business_idea_validation_get(
    user_request_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessIdeaValidationRunResponse:
    svc = BusinessIdeaValidationService(session, settings)
    result = await svc.get_latest(current_user.id, user_request_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="validation_not_found")
    return result


@router.get("/export")
async def business_idea_validation_export(
    user_request_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> dict[str, str]:
    from app.business_idea_validation.report_export import (
        build_customer_report_txt,
        validate_export_content,
    )

    svc = BusinessIdeaValidationService(session, settings)
    result = await svc.get_latest(current_user.id, user_request_id)
    if result is None or result.output is None or result.output.customer_report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="customer_report_not_found")
    text = build_customer_report_txt(report=result.output.customer_report, output=result.output)
    violations = validate_export_content(text)
    if violations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="export_validation_failed",
        )
    return {"content": text, "run_id": str(result.run_id)}


@router.get("/progress", response_model=BivRunProgress)
async def business_idea_validation_progress(
    user_request_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BivRunProgress:
    svc = BusinessIdeaValidationService(session, settings)
    progress = await svc.get_progress(current_user.id, user_request_id)
    if progress is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="progress_not_found")
    return progress


@router.get("/diagnostics", response_model=BivRunObservability)
async def business_idea_validation_diagnostics(
    user_request_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BivRunObservability:
    if settings.app_env not in {"development", "test", "pilot"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    svc = BusinessIdeaValidationService(session, settings)
    diagnostics = await svc.get_diagnostics(current_user.id, user_request_id)
    if diagnostics is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="diagnostics_not_found")
    return diagnostics


@router.get("/mcp-tools")
async def business_idea_validation_mcp_tools(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> list[dict]:
    _ = current_user
    client = McpClient(session, settings)
    return await client.list_tools()


@router.get("/audit", response_model=list[McpToolCallAuditRecord])
async def business_idea_validation_audit(
    user_request_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> list[McpToolCallAuditRecord]:
    repo = McpToolCallAuditRepository(session)
    rows = await repo.list_for_user_request(current_user.id, user_request_id)
    return [
        McpToolCallAuditRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            owner_id=row.owner_id,
            user_request_id=row.user_request_id,
            investigation_id=row.investigation_id,
            server_role=row.server_role,
            server_id=row.server_id,
            tool_name=row.tool_name,
            tool_schema_fingerprint=row.tool_schema_fingerprint,
            status=row.status,
            duration_ms=row.duration_ms,
            response_size_bytes=row.response_size_bytes,
            error_code=row.error_code,
            created_at=row.created_at,
        )
        for row in rows
    ]


@project_router.get("/latest", response_model=BusinessIdeaValidationProjectHydration)
async def business_idea_validation_project_latest(
    project_id: UUID,
    analysis_context_id: UUID | None = None,
    input_snapshot_hash: str | None = None,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessIdeaValidationProjectHydration:
    svc = BusinessIdeaValidationService(session, settings)
    result = await svc.get_project_hydration(
        current_user.id,
        project_id,
        analysis_context_id=analysis_context_id,
        input_snapshot_hash=input_snapshot_hash,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="validation_not_found")
    return result


@project_router.get("/latest-run", response_model=BusinessIdeaValidationProjectLatestRunSummary)
async def business_idea_validation_project_latest_run(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> BusinessIdeaValidationProjectLatestRunSummary:
    svc = BusinessIdeaValidationService(session, settings)
    result = await svc.get_project_latest_run(current_user.id, project_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="validation_run_not_found")
    return result
