"""Entrepreneur-facing video parameter preview — no paid gateway calls for long-form."""

from __future__ import annotations

from uuid import UUID

from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.media_generation.video_readiness import image_to_video_live_verified
from app.schemas.contracts import (
    VideoDurationMode,
    VideoSourceMode,
    VideoStudioPreviewPublic,
)
from app.video_studio.camera_movements import build_motion_prompt, resolve_camera_movement
from app.video_studio.contracts import (
    duration_mode_for,
    validate_aspect_ratio,
    validate_requested_duration,
)
from app.video_studio.long_form_planner import plan_long_form_scenes
from app.video_studio.router_capabilities import get_route_capabilities


def _aspect_availability(aspect: str, caps) -> tuple[str, str | None]:
    if aspect in caps.native_aspect_ratios:
        return "available", None
    if aspect in caps.post_process_aspect_ratios:
        return "post_process", "Потребуется кадрирование после генерации клипов."
    return "unavailable", "Формат недоступен для текущего видеоконтура."


def _cost_label(units: str | None, calls: int) -> str:
    if not units:
        return "уточняется перед созданием"
    try:
        total = float(units) * calls
        if total == int(total):
            return f"≈ {int(total)} ед. (по каталогу, {calls} клип.)"
        return f"≈ {total:.1f} ед. (по каталогу, {calls} клип.)"
    except ValueError:
        return f"≈ {units} ед. × {calls}"


class VideoStudioPreviewService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_preview(
        self,
        *,
        requested_duration_seconds: int,
        aspect_ratio: str,
        source_mode: VideoSourceMode,
        camera_movement_id: str,
        scene_description: str,
        camera_movement_instruction: str | None = None,
        start_asset_id: UUID | None = None,
        end_asset_id: UUID | None = None,
    ) -> VideoStudioPreviewPublic:
        seconds = validate_requested_duration(requested_duration_seconds)
        aspect = validate_aspect_ratio(aspect_ratio)
        resolve_camera_movement(camera_movement_id)
        if not scene_description.strip():
            raise InvalidStateError("scene_description_required")

        if source_mode == VideoSourceMode.START_END_FRAME:
            raise InvalidStateError("start_end_frame_not_available")

        if source_mode == VideoSourceMode.IMAGE and start_asset_id is None:
            raise InvalidStateError("start_asset_required")

        if end_asset_id is not None:
            raise InvalidStateError("end_asset_not_supported")

        caps = get_route_capabilities(self._settings)
        aspect_state, aspect_note = _aspect_availability(aspect.value, caps)
        if aspect_state == "unavailable":
            raise InvalidStateError("aspect_ratio_unavailable")

        mode = duration_mode_for(seconds)
        live = image_to_video_live_verified(self._settings)
        motion_prompt = build_motion_prompt(
            movement_id=camera_movement_id,
            instruction=camera_movement_instruction,
            scene_description=scene_description.strip(),
        )

        limitations: list[str] = []
        if aspect_state == "post_process":
            limitations.append(aspect_note or "Потребуется пост-обработка формата.")

        if mode == VideoDurationMode.LONG_FORM:
            plan = plan_long_form_scenes(seconds, caps)
            limitations.append(
                "Длинный ролик будет доступен после подключения сборки сцен. "
                "Сейчас можно подготовить сценарий и план сцен."
            )
            limitations.append("Ролик будет собран из нескольких сцен.")
            return VideoStudioPreviewPublic(
                duration_mode=mode,
                requested_duration_seconds=seconds,
                aspect_ratio=aspect.value,
                source_mode=source_mode,
                camera_movement_id=camera_movement_id,
                scene_description=scene_description.strip(),
                scene_count=plan.scene_count,
                scene_durations_seconds=plan.scene_durations_seconds,
                estimated_provider_calls=plan.estimated_provider_calls,
                estimated_cost_label=_cost_label(
                    caps.estimated_cost_units_per_clip,
                    plan.estimated_provider_calls,
                ),
                estimated_wait_seconds=plan.scene_count * 90,
                what_will_be_created_ru=(
                    f"План ролика {seconds} с ({aspect.value}) из {plan.scene_count} сцен."
                ),
                limitations_ru=limitations,
                generation_available=False,
                plan_only=True,
                primary_action_ru="Подготовить план ролика",
                blocked_reason_ru=None,
                approval_required=False,
                readiness_message_ru=(
                    "Сборка длинного ролика будет доступна после подключения AI Assembly."
                ),
            )

        # single clip
        limitations.append("Движение зависит от описания и возможностей видеодвижка.")
        ready = caps.router_connected and live and aspect_state != "unavailable"
        blocked: str | None = None
        if not caps.router_connected:
            blocked = "Генерация видео пока недоступна. Видеодвижок ещё не подключён."
        elif not live:
            blocked = (
                "Генерация видео пока недоступна. "
                "Функция будет активирована после проверки видеодвижка."
            )

        return VideoStudioPreviewPublic(
            duration_mode=mode,
            requested_duration_seconds=seconds,
            aspect_ratio=aspect.value,
            source_mode=source_mode,
            camera_movement_id=camera_movement_id,
            scene_description=scene_description.strip(),
            scene_count=1,
            scene_durations_seconds=[seconds],
            estimated_provider_calls=1,
            estimated_cost_label=_cost_label(caps.estimated_cost_units_per_clip, 1),
            estimated_wait_seconds=90,
            what_will_be_created_ru=(
                f"Короткий клип {seconds} с ({aspect.value}) по вашему описанию."
            ),
            limitations_ru=limitations,
            generation_available=ready,
            plan_only=False,
            primary_action_ru="Рассчитать стоимость",
            blocked_reason_ru=blocked,
            approval_required=True,
            readiness_message_ru=(
                "Готово к расчёту стоимости и созданию клипа."
                if ready
                else (blocked or "Создание клипа пока недоступно.")
            ),
            normalized_motion_prompt=motion_prompt,
        )
