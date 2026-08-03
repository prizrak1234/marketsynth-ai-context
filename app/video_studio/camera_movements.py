"""Camera movement presets — provisional until owner catalog is migrated."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.exceptions import InvalidStateError


class CameraMovementCompatibility(StrEnum):
    SINGLE_CLIP = "single_clip"
    LONG_FORM = "long_form"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class CameraMovementPreset:
    id: str
    label_ru: str
    label_en: str
    description_ru: str
    prompt_fragment_en: str
    compatible_modes: frozenset[CameraMovementCompatibility]
    provisional: bool = True


OWNER_CAMERA_MOVEMENTS_BLOCKER = {
    "status": "BLOCKER",
    "expected_owner_file": "Движение камеры и промпты.docx",
    "expected_path_external": (
        "C:/Users/User/Desktop/Обучение ИИ-агентам/Обучение ИИ-креативу/"
        "Модуль 4/Движение камеры и промпты.docx"
    ),
    "inventory_reference": "data/audits/workflow_corpus_inventory.json (dc-012386, priority_migration)",
    "searched_locations": [
        "docs/",
        "data/",
        "knowledge/",
        "workflows/",
        "standards/",
        "web/src/",
        "app/",
    ],
    "note_ru": (
        "Нормативный каталог не импортирован. Используется provisional fallback — "
        "требуется миграция owner-файла."
    ),
}


def _preset(
    id: str,
    label_ru: str,
    label_en: str,
    description_ru: str,
    prompt_fragment_en: str,
) -> CameraMovementPreset:
    return CameraMovementPreset(
        id=id,
        label_ru=label_ru,
        label_en=label_en,
        description_ru=description_ru,
        prompt_fragment_en=prompt_fragment_en,
        compatible_modes=frozenset({CameraMovementCompatibility.ALL}),
        provisional=True,
    )


PROVISIONAL_CAMERA_MOVEMENTS: tuple[CameraMovementPreset, ...] = (
    _preset("static", "Статичная камера", "Static camera", "Без движения камеры", "static camera, locked frame"),
    _preset("pan_left", "Панорама влево", "Pan left", "Горизонтальный поворот влево", "slow pan left"),
    _preset("pan_right", "Панорама вправо", "Pan right", "Горизонтальный поворот вправо", "slow pan right"),
    _preset("tilt_up", "Наклон вверх", "Tilt up", "Вертикальный наклон вверх", "slow tilt up"),
    _preset("tilt_down", "Наклон вниз", "Tilt down", "Вертикальный наклон вниз", "slow tilt down"),
    _preset("zoom_in", "Приближение", "Zoom in", "Плавное приближение", "slow zoom in"),
    _preset("zoom_out", "Отдаление", "Zoom out", "Плавное отдаление", "slow zoom out"),
    _preset("dolly_in", "Медленный наезд", "Dolly in", "Камера едет к объекту", "slow dolly in"),
    _preset("dolly_out", "Медленный отъезд", "Dolly out", "Камера отъезжает от объекта", "slow dolly out"),
    _preset("truck_left", "Параллакс влево", "Truck left", "Боковое смещение влево", "truck left"),
    _preset("truck_right", "Параллакс вправо", "Truck right", "Боковое смещение вправо", "truck right"),
    _preset("pedestal_up", "Подъём камеры", "Pedestal up", "Вертикальный подъём", "pedestal up"),
    _preset("pedestal_down", "Опускание камеры", "Pedestal down", "Вертикальный спуск", "pedestal down"),
    _preset("orbit_left", "Орбита влево", "Orbit left", "Облёт объекта влево", "orbit left around subject"),
    _preset("orbit_right", "Орбита вправо", "Orbit right", "Облёт объекта вправо", "orbit right around subject"),
    _preset("crane_up", "Кран вверх", "Crane up", "Подъём на кране", "crane up"),
    _preset("crane_down", "Кран вниз", "Crane down", "Опускание на кране", "crane down"),
    _preset("tracking", "Сопровождение", "Tracking shot", "Камера следует за объектом", "tracking shot"),
    _preset("follow", "Следование", "Follow", "Плавное следование за героем", "follow subject smoothly"),
    _preset("push_in", "Наезд", "Push in", "Короткий наезд на деталь", "push in"),
    _preset("pull_out", "Отъезд", "Pull out", "Короткий отъезд от сцены", "pull out"),
    _preset("handheld", "Ручная камера", "Handheld", "Лёгкая живость кадра", "subtle handheld motion"),
    _preset("steadicam", "Стеадикам", "Steadicam", "Плавное кинематографичное движение", "smooth steadicam move"),
    _preset("aerial", "Воздушный облёт", "Aerial", "Общий воздушный план", "aerial establishing shot"),
    _preset("drone_flyover", "Дрон-пролёт", "Drone flyover", "Пролёт над локацией", "drone flyover"),
    _preset("rack_focus", "Перевод фокуса", "Rack focus", "Смена фокуса между планами", "rack focus"),
    _preset("whip_pan", "Резкая панорама", "Whip pan", "Быстрый поворот камеры", "whip pan"),
    _preset("slow_cinematic_move", "Медленное кино-движение", "Slow cinematic move", "Спокойное кинематографичное движение", "slow cinematic camera move"),
)

_PRESET_BY_ID = {p.id: p for p in PROVISIONAL_CAMERA_MOVEMENTS}


def list_camera_movements() -> tuple[CameraMovementPreset, ...]:
    return PROVISIONAL_CAMERA_MOVEMENTS


def resolve_camera_movement(movement_id: str) -> CameraMovementPreset:
    key = (movement_id or "").strip()
    preset = _PRESET_BY_ID.get(key)
    if preset is None:
        raise InvalidStateError("unsupported_camera_movement")
    return preset


def build_motion_prompt(
    *,
    movement_id: str,
    instruction: str | None,
    scene_description: str,
) -> str:
    preset = resolve_camera_movement(movement_id)
    parts = [scene_description.strip(), preset.prompt_fragment_en]
    extra = (instruction or "").strip()
    if extra:
        parts.append(extra)
    return ". ".join(p for p in parts if p)
