"""H2.8E — non-biometric reference admission (upload ≠ admitted for identity)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.identity_generation.errors import identity_error_message
from app.schemas.contracts import (
    IdentityReferenceAdmissionStatus,
    ReferenceAssetPurpose,
    ReferenceExclusionReason,
    ReferenceQualityStatus,
)


@dataclass
class AdmissionResult:
    asset_id: UUID
    status: IdentityReferenceAdmissionStatus
    quality_status: ReferenceQualityStatus
    exclusion_code: str | None = None
    safe_reason: str | None = None
    suggestions: list[str] | None = None


def _min_side(width: int | None, height: int | None) -> int:
    if not width or not height:
        return 0
    return min(int(width), int(height))


def admit_reference_for_identity(
    *,
    asset_id: UUID,
    mime_type: str,
    width: int | None,
    height: int | None,
    byte_size: int,
    purpose: ReferenceAssetPurpose | str,
    quality_status: ReferenceQualityStatus | str,
    checksum: str,
    seen_checksums: set[str] | None = None,
    hard_invalid: bool = False,
) -> AdmissionResult:
    """Inspect → accept/classify/exclude. Never biometrics."""
    suggestions: list[str] = []
    purpose_s = purpose.value if hasattr(purpose, "value") else str(purpose)
    quality = (
        quality_status
        if isinstance(quality_status, ReferenceQualityStatus)
        else ReferenceQualityStatus(str(quality_status))
    )

    if hard_invalid or byte_size <= 0 or not (mime_type or "").startswith("image/"):
        return AdmissionResult(
            asset_id=asset_id,
            status=IdentityReferenceAdmissionStatus.REJECTED_TECHNICAL,
            quality_status=ReferenceQualityStatus.UNSUITABLE,
            exclusion_code=ReferenceExclusionReason.UNSUITABLE_QUALITY.value,
            safe_reason=identity_error_message("insufficient_reference_quality"),
        )

    if seen_checksums is not None and checksum in seen_checksums:
        return AdmissionResult(
            asset_id=asset_id,
            status=IdentityReferenceAdmissionStatus.EXCLUDED,
            quality_status=quality,
            exclusion_code=ReferenceExclusionReason.DUPLICATE_CHECKSUM.value,
            safe_reason="Дубликат файла (тот же checksum).",
        )

    min_side = _min_side(width, height)
    if min_side and min_side < 256:
        return AdmissionResult(
            asset_id=asset_id,
            status=IdentityReferenceAdmissionStatus.EXCLUDED,
            quality_status=ReferenceQualityStatus.UNSUITABLE,
            exclusion_code=ReferenceExclusionReason.LOW_RESOLUTION.value,
            safe_reason="Слишком низкое разрешение для референса внешности.",
            suggestions=["Загрузите фото не меньше 256×256."],
        )

    if quality == ReferenceQualityStatus.UNSUITABLE:
        return AdmissionResult(
            asset_id=asset_id,
            status=IdentityReferenceAdmissionStatus.EXCLUDED,
            quality_status=quality,
            exclusion_code=ReferenceExclusionReason.UNSUITABLE_QUALITY.value,
            safe_reason=identity_error_message("insufficient_reference_quality"),
        )

    if purpose_s in {
        ReferenceAssetPurpose.FULL_BODY.value,
        ReferenceAssetPurpose.BODY_REFERENCE.value,
        ReferenceAssetPurpose.POSE.value,
        ReferenceAssetPurpose.POSE_REFERENCE.value,
    }:
        suggestions.append("Фото тела/позы не может быть основным лицом.")

    if purpose_s in {
        ReferenceAssetPurpose.FACE_FRONT.value,
        ReferenceAssetPurpose.FACE_THREE_QUARTER.value,
        ReferenceAssetPurpose.FACE_PROFILE.value,
        ReferenceAssetPurpose.FACE_CLOSEUP.value,
        ReferenceAssetPurpose.FACE_REFERENCE.value,
    }:
        suggestions.append("Рекомендуется анфас / ¾ / профиль без сильных перекрытий.")

    return AdmissionResult(
        asset_id=asset_id,
        status=IdentityReferenceAdmissionStatus.ACCEPTED_FOR_REFERENCE,
        quality_status=quality if quality != ReferenceQualityStatus.PENDING else ReferenceQualityStatus.SUITABLE,
        suggestions=suggestions or None,
    )


def exclusion_safe_reason(code: str) -> str:
    mapping = {
        ReferenceExclusionReason.NOT_FACE_REFERENCE.value: "Не референс лица.",
        ReferenceExclusionReason.DUPLICATE_ANGLE.value: "Повторяющийся ракурс.",
        ReferenceExclusionReason.DUPLICATED_ANGLE.value: "Повторяющийся ракурс.",
        ReferenceExclusionReason.LOWER_QUALITY.value: "Ниже качество, чем у выбранного.",
        ReferenceExclusionReason.LOW_RESOLUTION.value: "Низкое разрешение.",
        ReferenceExclusionReason.BLUR.value: "Размытие.",
        ReferenceExclusionReason.BLURRED.value: "Размытие.",
        ReferenceExclusionReason.OCCLUSION.value: "Перекрытие лица.",
        ReferenceExclusionReason.OCCLUDED.value: "Перекрытие лица.",
        ReferenceExclusionReason.STYLE_ONLY.value: "Только для стиля/сцены.",
        ReferenceExclusionReason.BODY_ONLY.value: "Только тело/поза — не лицо.",
        ReferenceExclusionReason.PROVIDER_LIMIT.value: "Лимит провайдера.",
        ReferenceExclusionReason.DUPLICATE_CHECKSUM.value: "Дубликат файла.",
        ReferenceExclusionReason.INCONSISTENT_SUBJECT.value: "Возможно другой субъект.",
        ReferenceExclusionReason.USER_EXCLUDED.value: "Исключено вами.",
        ReferenceExclusionReason.UNSUITABLE_QUALITY.value: "Недостаточное качество.",
        ReferenceExclusionReason.BODY_NOT_PRIMARY.value: "Тело не может быть основным лицом.",
        ReferenceExclusionReason.NOT_SELECTED.value: "Не выбрано политикой.",
        ReferenceExclusionReason.PROVIDER_ADAPTER_LIMIT.value: (
            "Адаптер не передаёт этот референс провайдеру."
        ),
        ReferenceExclusionReason.SELECTED_BUT_NOT_TRANSMITTED.value: (
            "Выбрано, но провайдеру не передаётся."
        ),
    }
    return mapping.get(code, "Не использовано.")
