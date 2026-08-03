"""H2.8D — reference purpose groups and identity-aware selection."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.schemas.contracts import (
    ReferenceAssetPurpose,
    ReferenceExclusionReason,
    ReferencePurposeGroup,
    ReferenceQualityStatus,
    ReferenceSelectionResult,
    ReferenceSelectionRole,
    ReferenceSubjectType,
)

IDENTITY_PURPOSES: frozenset[ReferenceAssetPurpose] = frozenset(
    {
        ReferenceAssetPurpose.FACE_FRONT,
        ReferenceAssetPurpose.FACE_THREE_QUARTER,
        ReferenceAssetPurpose.FACE_PROFILE,
        ReferenceAssetPurpose.FACE_CLOSEUP,
        ReferenceAssetPurpose.FACE_REFERENCE,
        ReferenceAssetPurpose.IDENTITY_REFERENCE,
    }
)

APPEARANCE_PURPOSES: frozenset[ReferenceAssetPurpose] = frozenset(
    {
        ReferenceAssetPurpose.HAIR,
        ReferenceAssetPurpose.HALF_BODY,
        ReferenceAssetPurpose.FULL_BODY,
        ReferenceAssetPurpose.BODY_REFERENCE,
    }
)

SCENE_PURPOSES: frozenset[ReferenceAssetPurpose] = frozenset(
    {
        ReferenceAssetPurpose.CLOTHING,
        ReferenceAssetPurpose.OUTFIT_REFERENCE,
        ReferenceAssetPurpose.POSE,
        ReferenceAssetPurpose.POSE_REFERENCE,
        ReferenceAssetPurpose.STYLE_REFERENCE,
        ReferenceAssetPurpose.COMPOSITION_REFERENCE,
        ReferenceAssetPurpose.BACKGROUND_REFERENCE,
    }
)

BODY_PURPOSES: frozenset[ReferenceAssetPurpose] = frozenset(
    {
        ReferenceAssetPurpose.HALF_BODY,
        ReferenceAssetPurpose.FULL_BODY,
        ReferenceAssetPurpose.BODY_REFERENCE,
        ReferenceAssetPurpose.POSE,
        ReferenceAssetPurpose.POSE_REFERENCE,
        ReferenceAssetPurpose.OUTFIT_REFERENCE,
        ReferenceAssetPurpose.CLOTHING,
    }
)

_ROLE_LABELS_RU: dict[str, str] = {
    "face_front": "Основное лицо",
    "face_three_quarter": "Дополнительный ракурс",
    "face_profile": "Профиль",
    "face_closeup": "Крупный план",
    "face_reference": "Лицо",
    "identity_reference": "Идентичность",
    "hair": "Волосы",
    "half_body": "Полуфигура",
    "full_body": "Фигура",
    "body_reference": "Фигура",
    "clothing": "Одежда",
    "outfit_reference": "Одежда",
    "pose": "Поза",
    "pose_reference": "Поза",
    "style_reference": "Стиль",
    "composition_reference": "Композиция",
    "background_reference": "Фон",
    "other": "Прочее",
}


def purpose_group(purpose: ReferenceAssetPurpose | str) -> ReferencePurposeGroup:
    try:
        p = purpose if isinstance(purpose, ReferenceAssetPurpose) else ReferenceAssetPurpose(purpose)
    except ValueError:
        return ReferencePurposeGroup.OTHER
    if p in IDENTITY_PURPOSES:
        return ReferencePurposeGroup.IDENTITY
    if p in APPEARANCE_PURPOSES:
        return ReferencePurposeGroup.APPEARANCE
    if p in SCENE_PURPOSES:
        return ReferencePurposeGroup.SCENE
    return ReferencePurposeGroup.OTHER


def role_label_ru(purpose: str, *, is_primary: bool = False) -> str:
    if is_primary and purpose_group(purpose) == ReferencePurposeGroup.IDENTITY:
        return "Основное лицо"
    return _ROLE_LABELS_RU.get(purpose, purpose)


def is_body_purpose(purpose: ReferenceAssetPurpose | str) -> bool:
    try:
        p = purpose if isinstance(purpose, ReferenceAssetPurpose) else ReferenceAssetPurpose(purpose)
    except ValueError:
        return False
    return p in BODY_PURPOSES


def can_be_primary_face(purpose: ReferenceAssetPurpose | str) -> bool:
    """Body/pose/clothing photos must not become primary facial identity source."""
    return not is_body_purpose(purpose) and purpose_group(purpose) in {
        ReferencePurposeGroup.IDENTITY,
        ReferencePurposeGroup.OTHER,
    }


@dataclass(frozen=True)
class _RefView:
    id: UUID
    purpose: ReferenceAssetPurpose
    quality: ReferenceQualityStatus
    width: int
    height: int
    purposes: tuple[str, ...]


def _identity_slot_rank(purpose: ReferenceAssetPurpose) -> int:
    order = {
        ReferenceAssetPurpose.FACE_FRONT: 0,
        ReferenceAssetPurpose.FACE_REFERENCE: 1,
        ReferenceAssetPurpose.IDENTITY_REFERENCE: 2,
        ReferenceAssetPurpose.FACE_THREE_QUARTER: 3,
        ReferenceAssetPurpose.FACE_CLOSEUP: 4,
        ReferenceAssetPurpose.FACE_PROFILE: 5,
    }
    return order.get(purpose, 9)


def select_person_identity_refs(
    *,
    assets: list[_RefView],
    primary_reference_id: UUID | None,
    subject_type: ReferenceSubjectType,
    identity_max: int = 5,
    style_max: int = 1,
    appearance_max: int = 1,
) -> ReferenceSelectionResult:
    """Select ≤5 identity + optional appearance/scene; primary face first."""
    identity_max = max(1, min(int(identity_max), 5))
    stored = list(assets)
    roles: list[ReferenceSelectionRole] = []
    reasons: dict[str, str] = {}

    # Resolve primary — body photos cannot be primary face.
    primary = primary_reference_id
    blocked_primary: set[UUID] = set()
    if primary is not None:
        primary_asset = next((a for a in stored if a.id == primary), None)
        if primary_asset is not None and not can_be_primary_face(primary_asset.purpose):
            reasons[str(primary)] = ReferenceExclusionReason.BODY_NOT_PRIMARY.value
            blocked_primary.add(primary)
            primary = None

    identity_pool = [
        a
        for a in stored
        if purpose_group(a.purpose) == ReferencePurposeGroup.IDENTITY
        and a.quality != ReferenceQualityStatus.UNSUITABLE
        and a.id not in blocked_primary
    ]
    appearance_pool = [
        a
        for a in stored
        if purpose_group(a.purpose) == ReferencePurposeGroup.APPEARANCE
        and a.quality != ReferenceQualityStatus.UNSUITABLE
        and a.id not in blocked_primary
    ]
    scene_pool = [
        a
        for a in stored
        if purpose_group(a.purpose) == ReferencePurposeGroup.SCENE
        and a.quality != ReferenceQualityStatus.UNSUITABLE
        and a.id not in blocked_primary
    ]

    def _sort_identity(items: list[_RefView]) -> list[_RefView]:
        return sorted(
            items,
            key=lambda a: (
                0 if primary and a.id == primary else 1,
                _identity_slot_rank(a.purpose),
                -((a.width or 0) * (a.height or 0)),
            ),
        )

    # Prefer one of each angle family when possible.
    selected_identity: list[_RefView] = []
    seen_slots: set[int] = set()
    for a in _sort_identity(identity_pool):
        if len(selected_identity) >= identity_max:
            break
        slot = _identity_slot_rank(a.purpose)
        # Allow primary even if slot duplicate; otherwise skip duplicate angle.
        if slot in seen_slots and not (primary and a.id == primary):
            reasons[str(a.id)] = ReferenceExclusionReason.DUPLICATED_ANGLE.value
            continue
        selected_identity.append(a)
        seen_slots.add(slot)

    # Fill remaining identity slots with best remaining face refs.
    if len(selected_identity) < identity_max:
        remaining = [
            a for a in _sort_identity(identity_pool) if a.id not in {x.id for x in selected_identity}
        ]
        for a in remaining:
            if len(selected_identity) >= identity_max:
                break
            reasons.pop(str(a.id), None)
            selected_identity.append(a)

    selected_appearance = sorted(
        appearance_pool,
        key=lambda a: -((a.width or 0) * (a.height or 0)),
    )[:appearance_max]
    selected_scene = sorted(
        scene_pool,
        key=lambda a: -((a.width or 0) * (a.height or 0)),
    )[:style_max]

    selected_ids = [a.id for a in selected_identity + selected_appearance + selected_scene]
    # Primary must be first in transmitted order when present.
    if primary and primary in selected_ids:
        selected_ids = [primary] + [i for i in selected_ids if i != primary]
        # Ensure primary is in identity list metadata.
        if primary not in {a.id for a in selected_identity}:
            # Primary may be "other" — still transmit first for OpenAI edit.
            pass

    selected_set = set(selected_ids)
    for a in stored:
        group = purpose_group(a.purpose)
        is_sel = a.id in selected_set
        is_pri = bool(primary and a.id == primary)
        reason = reasons.get(str(a.id))
        if not is_sel and reason is None:
            if a.quality == ReferenceQualityStatus.UNSUITABLE:
                reason = ReferenceExclusionReason.UNSUITABLE_QUALITY.value
            elif group == ReferencePurposeGroup.IDENTITY and len(selected_identity) >= identity_max:
                reason = ReferenceExclusionReason.PROVIDER_LIMIT.value
            elif group == ReferencePurposeGroup.SCENE:
                reason = ReferenceExclusionReason.STYLE_ONLY.value
            elif group == ReferencePurposeGroup.APPEARANCE:
                reason = ReferenceExclusionReason.NOT_SELECTED.value
            elif group == ReferencePurposeGroup.OTHER:
                reason = ReferenceExclusionReason.NOT_FACE_REFERENCE.value
            else:
                reason = ReferenceExclusionReason.NOT_SELECTED.value
            reasons[str(a.id)] = reason
        roles.append(
            ReferenceSelectionRole(
                reference_id=a.id,
                purpose=a.purpose.value,
                group=group,
                role_label=role_label_ru(a.purpose.value, is_primary=is_pri),
                is_primary=is_pri,
                selected=is_sel,
                exclusion_reason=None if is_sel else reason,
            )
        )

    excluded_ids = [a.id for a in stored if a.id not in selected_set]
    identity_ids = [a.id for a in selected_identity]
    appearance_ids = [a.id for a in selected_appearance]
    scene_ids = [a.id for a in selected_scene]

    # For OpenAI images.edit: transmit primary first (single-image provider today).
    transmitted = list(selected_ids)
    if primary and primary in transmitted:
        transmitted = [primary] + [i for i in transmitted if i != primary]

    summary = (
        f"Загружено: {len(stored)}. "
        f"Для внешности выбрано: {len(identity_ids)}. "
        f"Для стиля выбрано: {len(scene_ids) + len(appearance_ids)}. "
        f"Не использовано: {len(excluded_ids)}."
    )
    if subject_type == ReferenceSubjectType.PERSON and len(identity_ids) < 3:
        summary += " Для лучшего сходства добавьте анфас, ¾ и профиль."

    return ReferenceSelectionResult(
        selected_reference_ids=selected_ids,
        excluded_reference_ids=excluded_ids,
        exclusion_reasons={k: v for k, v in reasons.items() if UUID(k) in set(excluded_ids)},
        max_provider_references=identity_max,
        selection_summary=summary,
        identity_selected_ids=identity_ids,
        appearance_selected_ids=appearance_ids,
        scene_selected_ids=scene_ids,
        identity_selected_count=len(identity_ids),
        style_selected_count=len(scene_ids) + len(appearance_ids),
        excluded_count=len(excluded_ids),
        stored_count=len(stored),
        roles=roles,
        transmitted_reference_ids=transmitted[:1],  # honest: OpenAI edit sends primary only
        primary_reference_id=primary if primary in selected_set else (transmitted[0] if transmitted else None),
    )


def views_from_rows(rows: list) -> list[_RefView]:
    """Build selection views from ReferenceVisualAssetTable rows."""
    out: list[_RefView] = []
    for row in rows:
        purpose = row.asset_purpose
        if not isinstance(purpose, ReferenceAssetPurpose):
            try:
                purpose = ReferenceAssetPurpose(str(purpose))
            except ValueError:
                purpose = ReferenceAssetPurpose.OTHER
        purposes = tuple(str(x) for x in (row.asset_purposes or []) if x)
        out.append(
            _RefView(
                id=row.id,
                purpose=purpose,
                quality=row.quality_status
                if isinstance(row.quality_status, ReferenceQualityStatus)
                else ReferenceQualityStatus(str(row.quality_status)),
                width=int(row.width or 0),
                height=int(row.height or 0),
                purposes=purposes,
            )
        )
    return out
