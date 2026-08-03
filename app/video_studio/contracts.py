"""VS.2B — single source of truth for Video Studio parameters."""

from __future__ import annotations

from enum import StrEnum

from app.core.exceptions import InvalidStateError


class VideoDurationMode(StrEnum):
    SINGLE_CLIP = "single_clip"
    LONG_FORM = "long_form"


class VideoAspectRatio(StrEnum):
    PORTRAIT_9_16 = "9:16"
    LANDSCAPE_16_9 = "16:9"
    SQUARE_1_1 = "1:1"
    PORTRAIT_4_5 = "4:5"
    CINEMATIC_21_9 = "21:9"


class VideoSourceMode(StrEnum):
    NO_START_FRAME = "no_start_frame"
    IMAGE = "image"
    START_END_FRAME = "start_end_frame"


REQUESTED_VIDEO_DURATION_SECONDS: tuple[int, ...] = (
    5,
    8,
    10,
    15,
    30,
    60,
    90,
    120,
    180,
    300,
)

SINGLE_CLIP_DURATION_SECONDS: frozenset[int] = frozenset({5, 8, 10, 15})
LONG_FORM_DURATION_SECONDS: frozenset[int] = frozenset({30, 60, 90, 120, 180, 300})

_ASPECT_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": VideoAspectRatio.PORTRAIT_9_16.value,
        "label_ru": "9:16 — Reels / Shorts / TikTok",
        "label_en": "9:16 — Reels / Shorts / TikTok",
        "purpose_ru": "Вертикальные соцсети",
    },
    {
        "id": VideoAspectRatio.LANDSCAPE_16_9.value,
        "label_ru": "16:9 — YouTube / презентации",
        "label_en": "16:9 — YouTube / presentations",
        "purpose_ru": "Горизонтальное видео",
    },
    {
        "id": VideoAspectRatio.SQUARE_1_1.value,
        "label_ru": "1:1 — квадратная публикация",
        "label_en": "1:1 — square post",
        "purpose_ru": "Квадратные площадки",
    },
    {
        "id": VideoAspectRatio.PORTRAIT_4_5.value,
        "label_ru": "4:5 — лента соцсетей",
        "label_en": "4:5 — social feed",
        "purpose_ru": "Вертикальный пост в ленте",
    },
    {
        "id": VideoAspectRatio.CINEMATIC_21_9.value,
        "label_ru": "21:9 — cinematic / widescreen",
        "label_en": "21:9 — cinematic / widescreen",
        "purpose_ru": "Кинематографический формат",
    },
)


def aspect_ratio_catalog() -> tuple[dict[str, str], ...]:
    return _ASPECT_CATALOG


def validate_requested_duration(seconds: int) -> int:
    if seconds not in REQUESTED_VIDEO_DURATION_SECONDS:
        raise InvalidStateError("unsupported_video_duration")
    return seconds


def validate_aspect_ratio(value: str) -> VideoAspectRatio:
    try:
        return VideoAspectRatio(value)
    except ValueError as exc:
        raise InvalidStateError("unsupported_aspect_ratio") from exc


def duration_mode_for(seconds: int) -> VideoDurationMode:
    validate_requested_duration(seconds)
    if seconds in SINGLE_CLIP_DURATION_SECONDS:
        return VideoDurationMode.SINGLE_CLIP
    return VideoDurationMode.LONG_FORM


def is_single_clip_duration(seconds: int) -> bool:
    return duration_mode_for(seconds) == VideoDurationMode.SINGLE_CLIP
