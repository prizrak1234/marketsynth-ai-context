"""Provider truth for single-clip duration — VS.2A-R duration contract."""

from __future__ import annotations

from app.core.exceptions import InvalidStateError

# Reasonable tolerance for single-clip commercial jobs (±0.5 sec).
SINGLE_CLIP_DURATION_TOLERANCE_SECONDS = 0.5

# GPTunnel CreativeLab Veo family: fixed ~8s clips; duration is not in create payload.
_VEO_FAMILY_FIXED_SECONDS = 8
_VEO_MODEL_PREFIXES = ("glabs-veo-", "veo-")

_PROVIDER_SINGLE_CLIP_DURATIONS: dict[str, tuple[int, ...]] = {
    "glabs-veo-3-1-fast": (_VEO_FAMILY_FIXED_SECONDS,),
    "glabs-veo-3-fast": (_VEO_FAMILY_FIXED_SECONDS,),
    "glabs-veo-3": (_VEO_FAMILY_FIXED_SECONDS,),
}


def _normalize_model(model: str | None) -> str:
    return (model or "").strip().lower()


def is_veo_family_model(model: str | None) -> bool:
    normalized = _normalize_model(model)
    return any(normalized.startswith(prefix) for prefix in _VEO_MODEL_PREFIXES)


def provider_supported_single_clip_durations(model: str | None) -> tuple[int, ...]:
    """Return exact durations the active provider/model can deliver for single clips."""
    normalized = _normalize_model(model)
    if normalized in _PROVIDER_SINGLE_CLIP_DURATIONS:
        return _PROVIDER_SINGLE_CLIP_DURATIONS[normalized]
    if is_veo_family_model(normalized):
        return (_VEO_FAMILY_FIXED_SECONDS,)
    return ()


def assert_single_clip_duration_supported(seconds: int, model: str | None) -> None:
    supported = provider_supported_single_clip_durations(model)
    if not supported:
        return
    if seconds not in supported:
        raise InvalidStateError("provider_duration_not_supported")


def provider_payload_duration_seconds(model: str | None) -> int | None:
    """Duration field sent to provider create payload — None when not transmitted."""
    _ = model
    # GPTunnel CreativeLab media/create for Veo does not accept a duration parameter.
    return None


def provider_reported_duration_seconds(model: str | None) -> int | None:
    """Provider-documented clip length when API does not return per-job duration."""
    supported = provider_supported_single_clip_durations(model)
    if len(supported) == 1:
        return supported[0]
    return None
