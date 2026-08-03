"""Video Studio VS.2B — capabilities + parameter preview (commercial slice)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies.auth import require_active_user
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.core.security import sanitize_payload
from app.db.models.user import UserTable
from app.schemas.contracts import (
    VideoSourceMode,
    VideoStudioCapabilitiesPublic,
    VideoStudioPreviewPublic,
)
from app.video_studio.capabilities_service import build_video_studio_capabilities
from app.video_studio.preview_service import VideoStudioPreviewService

router = APIRouter(prefix="/media-generation/video-studio", tags=["media-generation"])


class VideoStudioPreviewBody(BaseModel):
    requested_duration_seconds: int
    aspect_ratio: str = Field(default="16:9", max_length=16)
    source_mode: VideoSourceMode = VideoSourceMode.NO_START_FRAME
    start_asset_id: UUID | None = None
    end_asset_id: UUID | None = None
    camera_movement_id: str = Field(..., min_length=2, max_length=64)
    camera_movement_instruction: str | None = Field(default=None, max_length=500)
    scene_description: str = Field(..., min_length=4, max_length=4000)


def _map_contract_error(exc: InvalidStateError) -> HTTPException:
    code = str(exc)
    status_code = status.HTTP_400_BAD_REQUEST
    if code in {"aspect_ratio_unavailable", "start_end_frame_not_available"}:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=code)


@router.get("/capabilities", response_model=VideoStudioCapabilitiesPublic)
async def get_video_studio_capabilities(
    settings: Settings = Depends(get_settings),
    _current_user: UserTable = Depends(require_active_user),
) -> VideoStudioCapabilitiesPublic:
    return build_video_studio_capabilities(settings)


@router.post("/preview", response_model=VideoStudioPreviewPublic)
async def preview_video_parameters(
    body: VideoStudioPreviewBody,
    settings: Settings = Depends(get_settings),
    _current_user: UserTable = Depends(require_active_user),
) -> VideoStudioPreviewPublic:
    svc = VideoStudioPreviewService(settings)
    try:
        return svc.build_preview(
            requested_duration_seconds=body.requested_duration_seconds,
            aspect_ratio=body.aspect_ratio,
            source_mode=body.source_mode,
            camera_movement_id=body.camera_movement_id.strip(),
            camera_movement_instruction=sanitize_payload(body.camera_movement_instruction or ""),
            scene_description=sanitize_payload(body.scene_description),
            start_asset_id=body.start_asset_id,
            end_asset_id=body.end_asset_id,
        )
    except InvalidStateError as exc:
        raise _map_contract_error(exc) from exc
