"""VS.2A entrepreneur-facing video clip API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_active_user, require_role
from app.api.deps import get_session
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload
from app.db.models.user import UserTable
from app.schemas.contracts import (
    UserRole,
    VideoClipExecutionPublic,
    VideoClipHydrationPublic,
    VideoClipPreviewPublic,
    VideoOwnerAcceptancePreviewPublic,
)
from app.services.video_clip_commercial_service import VideoClipCommercialService

router = APIRouter(prefix="/media-generation/video-clips", tags=["media-generation"])


@router.get("/owner-acceptance-preview", response_model=VideoOwnerAcceptancePreviewPublic)
async def owner_acceptance_preview(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> VideoOwnerAcceptancePreviewPublic:
    """Owner/admin read-only binding for canonical smoke clip acceptance."""
    svc = VideoClipCommercialService(session, settings)
    try:
        return await svc.get_owner_acceptance_preview()
    except InvalidStateError as exc:
        raise _map_error(exc) from exc


@router.get("", response_model=VideoClipHydrationPublic | None)
async def get_video_clip_by_source(
    source_image_asset_id: UUID,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VideoClipHydrationPublic | None:
    svc = VideoClipCommercialService(session, settings)
    return await svc.get_by_source_image(
        owner_id=current_user.id,
        source_image_asset_id=source_image_asset_id,
    )


class VideoClipPreviewBody(BaseModel):
    source_image_asset_id: UUID
    motion_brief: str = Field(..., min_length=4, max_length=4000)
    duration_seconds: int = Field(default=8, ge=5, le=300)
    aspect_ratio: str = Field(default="16:9", max_length=16)
    camera_movement_id: str | None = Field(default=None, max_length=64)
    camera_movement_instruction: str | None = Field(default=None, max_length=500)
    project_id: UUID | None = None
    user_request_id: UUID | None = None


class VideoClipGenerateBody(BaseModel):
    approved: bool = Field(..., description="Explicit approval after cost preview.")


def _map_error(exc: InvalidStateError) -> HTTPException:
    code = str(exc)
    status_code = status.HTTP_409_CONFLICT
    if code in {"source_asset_not_found", "clip_request_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    if code == "reconcile_requires_provider_job_id":
        status_code = status.HTTP_409_CONFLICT
    if code == "clip_request_not_reconcilable":
        status_code = status.HTTP_409_CONFLICT
    if code in {"approval_required", "idempotency_key_required"}:
        status_code = status.HTTP_400_BAD_REQUEST
    if code in {
        "unsupported_video_duration",
        "unsupported_aspect_ratio",
        "unsupported_camera_movement",
        "provider_duration_not_supported",
    }:
        status_code = status.HTTP_400_BAD_REQUEST
    if code in {
        "source_asset_not_accepted",
        "source_asset_not_ready",
        "source_asset_identity_reference_blocked",
        "source_asset_not_image",
        "source_asset_file_missing",
    }:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=code)


@router.post("/preview", response_model=VideoClipPreviewPublic)
async def preview_video_clip(
    body: VideoClipPreviewBody,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VideoClipPreviewPublic:
    svc = VideoClipCommercialService(session, settings)
    try:
        return await svc.create_preview(
            owner_id=current_user.id,
            source_image_asset_id=body.source_image_asset_id,
            motion_brief=sanitize_payload(body.motion_brief),
            duration_seconds=body.duration_seconds,
            aspect_ratio=body.aspect_ratio,
            project_id=body.project_id,
            user_request_id=body.user_request_id,
            camera_movement_id=body.camera_movement_id,
            camera_movement_instruction=sanitize_payload(body.camera_movement_instruction or ""),
        )
    except InvalidStateError as exc:
        raise _map_error(exc) from exc


@router.post("/{clip_request_id}/generate", response_model=VideoClipExecutionPublic)
async def generate_video_clip(
    clip_request_id: UUID,
    body: VideoClipGenerateBody,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_active_user),
) -> VideoClipExecutionPublic:
    svc = VideoClipCommercialService(session, settings)
    try:
        return await svc.generate_approved(
            owner_id=current_user.id,
            clip_request_id=clip_request_id,
            idempotency_key=idempotency_key.strip(),
            approved=body.approved,
        )
    except InvalidStateError as exc:
        raise _map_error(exc) from exc


@router.post("/{clip_request_id}/reconcile", response_model=VideoClipExecutionPublic)
async def reconcile_video_clip(
    clip_request_id: UUID,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
    current_user: UserTable = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> VideoClipExecutionPublic:
    svc = VideoClipCommercialService(session, settings)
    try:
        return await svc.reconcile(
            owner_id=current_user.id,
            clip_request_id=clip_request_id,
        )
    except InvalidStateError as exc:
        raise _map_error(exc) from exc
