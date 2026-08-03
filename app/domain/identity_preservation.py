"""Identity preservation helpers (Phase H2.8B)."""

from __future__ import annotations

from uuid import UUID

from app.schemas.contracts import (
    IdentityPreservationProfile,
    VisualConsistencyLevel,
)


_DEFAULT_IMMUTABLE = [
    "facial_geometry",
    "eye_shape",
    "nose_shape",
    "lip_shape",
    "skin_tone",
    "apparent_age",
    "distinctive_features",
    "hair_color",
    "hair_style",
]


def build_identity_profile(
    *,
    primary_reference_id: UUID | None,
    reference_asset_ids: list[UUID],
    immutable_traits: list[str] | None = None,
    allowed_variations: list[str] | None = None,
    forbidden_changes: list[str] | None = None,
    user_notes: str | None = None,
    strengthen_mode: bool = False,
) -> IdentityPreservationProfile:
    traits = list(immutable_traits or _DEFAULT_IMMUTABLE)
    profile = IdentityPreservationProfile(
        version="1.0",
        primary_reference_id=primary_reference_id,
        reference_asset_ids=list(reference_asset_ids),
        allowed_changes=list(
            allowed_variations
            or [
                "clothing",
                "background",
                "lighting",
                "pose_within_limits",
                "artistic_setting",
            ]
        ),
        forbidden_changes=list(
            forbidden_changes
            or [
                "replace_person",
                "change_ethnicity",
                "material_age_change",
                "core_facial_proportions",
                "unrelated_facial_features",
            ]
        ),
        user_notes=user_notes,
        strengthen_mode=strengthen_mode,
    )
    # Map trait names into boolean flags when present
    lower = {t.lower() for t in traits}
    if "hair" in lower or "hair_color" in lower:
        profile.preserve_hair_color = True
    if strengthen_mode:
        profile.allowed_changes = [
            c for c in profile.allowed_changes if c not in {"pose_within_limits"}
        ]
        if "artistic_setting" in profile.allowed_changes:
            profile.allowed_changes = [
                c for c in profile.allowed_changes if c != "artistic_setting"
            ]
    return profile


def build_identity_prompt_sections(
    *,
    scene_prompt: str,
    profile: IdentityPreservationProfile,
) -> str:
    """Structured provider prompt — identity first, scene second (legacy combined)."""
    parts = build_separated_provider_inputs(scene_prompt=scene_prompt, profile=profile)
    from app.media_generation.identity_provider import build_prompt_sections

    return build_prompt_sections(
        identity_section=parts["identity"],
        scene_section=parts["scene"],
        style_section=parts["style"],
        negative_section=parts["negative"],
    )


def build_separated_provider_inputs(
    *,
    scene_prompt: str,
    profile: IdentityPreservationProfile,
) -> dict[str, str]:
    """H2.8D — IDENTITY / SCENE / STYLE / NEGATIVE as separate sections."""
    immutable = []
    if profile.preserve_face_structure:
        immutable.append("facial geometry")
    if profile.preserve_eye_shape:
        immutable.append("eye shape")
    if profile.preserve_nose_shape:
        immutable.append("nose shape")
    if profile.preserve_lip_shape:
        immutable.append("lip shape")
    if profile.preserve_skin_tone:
        immutable.append("skin tone")
    if profile.preserve_apparent_age:
        immutable.append("apparent age")
    if profile.preserve_hair_color:
        immutable.append("hair color")
    if profile.preserve_hair_style:
        immutable.append("hair style")
    if profile.preserve_distinctive_features:
        immutable.append("distinctive features")
    if profile.preserve_body_proportions:
        immutable.append("body proportions")

    strengthen = (
        "Increase identity priority: minimize stylistic freedom; "
        "match the primary reference face as closely as generative models allow."
        if profile.strengthen_mode
        else ""
    )
    identity = "\n".join(
        s
        for s in [
            "Preserve the recognizable person from the primary and supporting face references.",
            "Maintain: " + ", ".join(immutable) + ".",
            strengthen,
            f"Owner notes: {profile.user_notes}" if profile.user_notes else "",
        ]
        if s
    )
    scene = (scene_prompt or "").strip()[:3200]
    style = "photorealistic; cinematic; respect palette and lighting from the scene description."
    negative = (
        "do not replace the subject; "
        "do not significantly change face shape; "
        "do not change apparent age; "
        "do not average multiple different identities; "
        + ", ".join(profile.forbidden_changes)
    )
    return {
        "identity": identity,
        "scene": scene,
        "style": style,
        "negative": negative,
    }


def assess_visual_consistency_assist(
    *,
    used_reference_count: int,
    strengthen_mode: bool,
    generation_mode: str,
    transmitted_count: int | None = None,
) -> VisualConsistencyLevel:
    """Heuristic helper only — never biometric identity proof."""
    tx = transmitted_count if transmitted_count is not None else used_reference_count
    if tx <= 0 or generation_mode in {"text_to_image", "reference_guided_style"}:
        if generation_mode == "person_identity_preservation" and tx <= 0:
            return VisualConsistencyLevel.UNAVAILABLE
        if generation_mode == "text_to_image":
            return VisualConsistencyLevel.UNAVAILABLE
    if generation_mode == "person_identity_preservation":
        # Single primary transmit is common for OpenAI edit — do not auto-claim medium.
        if strengthen_mode:
            return VisualConsistencyLevel.MEDIUM
        return VisualConsistencyLevel.LOW
    if used_reference_count >= 3 and strengthen_mode:
        return VisualConsistencyLevel.MEDIUM
    if used_reference_count >= 3:
        return VisualConsistencyLevel.MEDIUM
    if used_reference_count == 1:
        return VisualConsistencyLevel.LOW
    return VisualConsistencyLevel.MEDIUM


def consistency_user_message(level: VisualConsistencyLevel) -> str | None:
    if level == VisualConsistencyLevel.LOW:
        return (
            "Результат недостаточно похож на выбранные референсы и не принят системой. "
            "Можно: повторить с основным референсом; уменьшить стилизацию; "
            "выбрать другие референсы; использовать специализированный режим."
        )
    if level == VisualConsistencyLevel.UNAVAILABLE:
        return None
    return None


MSG_IDENTITY_MODE_UNSUPPORTED = (
    "Текущий генератор не обеспечивает требуемое сохранение внешности. "
    "Выберите другой режим или подключите специализированный генератор."
)

MSG_QUALITY_GATE_REJECTED = (
    "Результат недостаточно похож на выбранные референсы и не принят системой."
)