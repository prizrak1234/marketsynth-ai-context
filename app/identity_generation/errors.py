"""H2.8E — normalized identity subsystem errors → Russian UI copy."""

from __future__ import annotations

IDENTITY_ERROR_MESSAGES_RU: dict[str, str] = {
    "identity_mode_not_supported": "Текущий генератор не поддерживает сохранение внешности.",
    "primary_reference_required": "Выберите основное фото лица.",
    "insufficient_reference_quality": "Качество основных референсов недостаточно.",
    "paid_approval_required": "Для тестовой генерации требуется подтверждение расходов.",
    "provider_adapter_limit": "Этот генератор использует только основной референс.",
    "low_visual_consistency": "Сходство с референсами недостаточно.",
    "provider_unavailable": "Генератор временно недоступен.",
    "consent_required": "Подтвердите согласие на использование референсов.",
    "reference_set_required": "Загрузите набор референсов.",
    "reference_set_empty": "В наборе нет принятых изображений.",
    "identity_profile_required": "Профиль сохранения внешности не собран.",
    "prompt_insufficient": "Опишите сцену подробнее.",
    "credentials_missing": "Генератор не настроен (нет ключа провайдера).",
    "owner_mismatch": "Набор референсов принадлежит другому пользователю.",
    "preflight_blocked": "Генерация заблокирована проверками готовности.",
    "selected_but_not_transmitted": (
        "Текущий генератор использовал 1 основной референс. "
        "Дополнительные ракурсы сохранены, но этим провайдером не передаются."
    ),
}


def identity_error_message(code: str, *, fallback: str | None = None) -> str:
    key = (code or "").strip()
    if key in IDENTITY_ERROR_MESSAGES_RU:
        return IDENTITY_ERROR_MESSAGES_RU[key]
    if fallback:
        return fallback
    return "Не удалось выполнить генерацию с сохранением внешности."
