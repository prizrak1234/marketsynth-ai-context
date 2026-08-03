"""Build entrepreneur-facing capabilities payload."""

from __future__ import annotations

from app.core.config import Settings
from app.media_generation.video_readiness import image_to_video_live_verified
from app.schemas.contracts import (
    CameraMovementOptionPublic,
    VideoAspectRatioOptionPublic,
    VideoStudioCapabilitiesPublic,
)
from app.video_studio.camera_movements import (
    OWNER_CAMERA_MOVEMENTS_BLOCKER,
    list_camera_movements,
)
from app.video_studio.contracts import REQUESTED_VIDEO_DURATION_SECONDS, aspect_ratio_catalog
from app.video_studio.router_capabilities import get_route_capabilities


def build_video_studio_capabilities(settings: Settings) -> VideoStudioCapabilitiesPublic:
    caps = get_route_capabilities(settings)
    live = image_to_video_live_verified(settings)
    single_ready = caps.router_connected and live

    aspect_options: list[VideoAspectRatioOptionPublic] = []
    for row in aspect_ratio_catalog():
        ratio_id = row["id"]
        if ratio_id in caps.native_aspect_ratios:
            state = "available"
            reason_ru = None
        elif ratio_id in caps.post_process_aspect_ratios:
            state = "post_process"
            reason_ru = "Формат будет подготовлен с кадрированием после генерации клипов."
        else:
            state = "unavailable"
            reason_ru = "Формат пока недоступен для текущего видеоконтура."

        aspect_options.append(
            VideoAspectRatioOptionPublic(
                id=ratio_id,
                label_ru=row["label_ru"],
                label_en=row["label_en"],
                purpose_ru=row["purpose_ru"],
                availability=state,
                disabled_reason_ru=reason_ru if state != "available" else None,
            )
        )

    movements = [
        CameraMovementOptionPublic(
            id=p.id,
            label_ru=p.label_ru,
            label_en=p.label_en,
            description_ru=p.description_ru,
            provisional=p.provisional,
        )
        for p in list_camera_movements()
    ]

    return VideoStudioCapabilitiesPublic(
        requested_durations_seconds=list(REQUESTED_VIDEO_DURATION_SECONDS),
        provider_supported_single_clip_durations_seconds=list(
            caps.provider_supported_single_clip_durations_seconds
        ),
        single_clip_max_seconds=caps.single_clip_max_seconds,
        single_clip_min_seconds=caps.single_clip_min_seconds,
        target_scene_duration_seconds=caps.target_scene_duration_seconds,
        aspect_ratios=aspect_options,
        camera_movements=movements,
        camera_movements_catalog_status=OWNER_CAMERA_MOVEMENTS_BLOCKER["status"],
        camera_movements_catalog_note_ru=OWNER_CAMERA_MOVEMENTS_BLOCKER["note_ru"],
        long_form_planning_available=True,
        long_form_generation_available=False,
        start_end_frame_available=False,
        single_clip_generation_available=single_ready,
        assembly_pipeline_ready=False,
    )
