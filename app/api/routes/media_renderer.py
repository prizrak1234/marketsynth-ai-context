"""Media Renderer API — governed Higgsfield MCP execution path (CONN-HF-01.1)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import require_active_user
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.db.models.user import UserTable
from app.schemas.contracts import (
    MediaRendererReadiness,
    MediaRenderJobResponse,
    MediaRenderRequest,
    UserRole,
)
from app.services.media_renderer_service import MediaRendererService

router = APIRouter(
    prefix="/projects/{project_id}/media-renderer",
    tags=["media-renderer"],
)


def _live_allowed(current_user: UserTable, settings: Settings) -> bool:
    if not settings.higgsfield_owner_sandbox_enabled:
        return False
    return current_user.role in (UserRole.OWNER, UserRole.ADMIN)


def _map_error(exc: Exception) -> HTTPException:
    code = str(exc)
    if code in {
        "explicit_confirmation_required",
        "approval_reference_required",
        "render_spec_incomplete",
        "upstream_skill_not_allowed",
        "billing_cost_unknown_acceptance_required",
    }:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)
    if code in {
        "higgsfield_video_render_disabled",
        "higgsfield_mcp_disabled",
        "connector_not_production_ready",
    }:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)
    if code.startswith("connector_") or code.endswith("_denied"):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=code)
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)


@router.get("/readiness", response_model=MediaRendererReadiness)
async def media_renderer_readiness(
    project_id: UUID,  # noqa: ARG001 — scope guard for future project checks
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),  # noqa: ARG001
) -> MediaRendererReadiness:
    svc = MediaRendererService(settings)
    return await svc.readiness()


@router.post("/render", response_model=MediaRenderJobResponse)
async def media_renderer_render(
    project_id: UUID,
    body: MediaRenderRequest,
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> MediaRenderJobResponse:
    svc = MediaRendererService(settings)
    try:
        return await svc.render(
            owner_id=current_user.id,
            project_id=project_id,
            body=body,
            live_allowed=_live_allowed(current_user, settings),
        )
    except InvalidStateError as exc:
        raise _map_error(exc) from exc


@router.get("/jobs/{job_id}/status", response_model=MediaRenderJobResponse)
async def media_renderer_job_status(
    project_id: UUID,
    job_id: str,
    upstream_skill_id: str,
    dry_run: bool = True,
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> MediaRenderJobResponse:
    svc = MediaRendererService(settings)
    try:
        return await svc.get_status(
            owner_id=current_user.id,
            project_id=project_id,
            job_id=job_id,
            upstream_skill_id=upstream_skill_id,
            dry_run=dry_run,
            live_allowed=_live_allowed(current_user, settings),
        )
    except InvalidStateError as exc:
        raise _map_error(exc) from exc


@router.get("/jobs/{job_id}/download", response_model=MediaRenderJobResponse)
async def media_renderer_job_download(
    project_id: UUID,
    job_id: str,
    upstream_skill_id: str,
    dry_run: bool = True,
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_active_user),
) -> MediaRenderJobResponse:
    svc = MediaRendererService(settings)
    try:
        return await svc.download_result(
            owner_id=current_user.id,
            project_id=project_id,
            job_id=job_id,
            upstream_skill_id=upstream_skill_id,
            dry_run=dry_run,
            live_allowed=_live_allowed(current_user, settings),
        )
    except InvalidStateError as exc:
        raise _map_error(exc) from exc
