"""H2.8E — Identity Provider Registry (no secrets)."""

from __future__ import annotations

from app.core.config import Settings
from app.schemas.contracts import (
    IdentityProviderCapability,
    IdentityProviderCostPolicy,
    IdentityProviderDefinition,
    IdentityProviderHealthStatus,
    VisualExecutionMode,
)


def _has_openai(settings: Settings) -> bool:
    key = settings.openai_api_key
    return bool(key and key.get_secret_value().strip())


def _has_gptunnel(settings: Settings) -> bool:
    key = getattr(settings, "gptunnel_api_key", None)
    return bool(key and key.get_secret_value().strip())


def build_identity_provider_registry(settings: Settings) -> list[IdentityProviderDefinition]:
    """Single authoritative registry for identity-capable adapters."""
    enabled = bool(settings.image_generation_enabled)
    active = (settings.image_generation_provider or "mock").strip().lower()

    openai_configured = _has_openai(settings)
    openai = IdentityProviderDefinition(
        provider_code="openai_images",
        adapter_code="OpenAIIdentityAdapter",
        enabled=enabled and active == "openai_images",
        configured=openai_configured,
        health_status=(
            IdentityProviderHealthStatus.HEALTHY
            if openai_configured and enabled
            else IdentityProviderHealthStatus.UNAVAILABLE
        ),
        supported_modes=[
            VisualExecutionMode.TEXT_TO_IMAGE,
            VisualExecutionMode.IMAGE_EDIT,
            VisualExecutionMode.PERSON_IDENTITY_PRESERVATION,  # soft: primary-only
        ],
        maximum_identity_images=1,  # honest: images.edit sends primary only
        supports_primary_reference=True,
        supports_supporting_references=False,
        supports_style_reference=False,
        supports_identity_strength=False,
        supports_style_strength=False,
        supports_seed=False,
        supports_image_edit=True,
        supports_async_jobs=False,
        cost_policy=IdentityProviderCostPolicy.PAID_PER_CALL,
        approval_required=True,
        known_limitations=[
            "primary_reference_only",
            "supporting_refs_selected_but_not_transmitted",
            "not_a_specialized_identity_engine",
        ],
        last_verified_at=None,
        capability_status=IdentityProviderCapability.UNVERIFIED,
    )

    gptunnel_configured = _has_gptunnel(settings)
    gptunnel = IdentityProviderDefinition(
        provider_code="gptunnel_images",
        adapter_code="UnsupportedIdentityAdapter",
        enabled=False,  # fail-closed for identity
        configured=gptunnel_configured,
        health_status=IdentityProviderHealthStatus.UNAVAILABLE,
        supported_modes=[VisualExecutionMode.TEXT_TO_IMAGE],
        maximum_identity_images=0,
        supports_primary_reference=False,
        supports_supporting_references=False,
        supports_style_reference=False,
        supports_identity_strength=False,
        supports_style_strength=False,
        supports_seed=False,
        supports_image_edit=False,
        supports_async_jobs=False,
        cost_policy=IdentityProviderCostPolicy.PAID_PER_CALL,
        approval_required=True,
        known_limitations=[
            "text_to_image_only",
            "identity_mode_not_supported",
            "fail_closed_with_references",
        ],
        last_verified_at=None,
        capability_status=IdentityProviderCapability.UNSUITABLE_FOR_IDENTITY,
    )

    specialized = IdentityProviderDefinition(
        provider_code="specialized_identity_reserved",
        adapter_code="ReservedIdentityAdapter",
        enabled=False,
        configured=False,
        health_status=IdentityProviderHealthStatus.UNAVAILABLE,
        supported_modes=[VisualExecutionMode.PERSON_IDENTITY_PRESERVATION],
        maximum_identity_images=5,
        supports_primary_reference=True,
        supports_supporting_references=True,
        supports_style_reference=True,
        supports_identity_strength=True,
        supports_style_strength=True,
        supports_seed=True,
        supports_image_edit=True,
        supports_async_jobs=True,
        cost_policy=IdentityProviderCostPolicy.UNKNOWN,
        approval_required=True,
        known_limitations=["not_integrated"],
        last_verified_at=None,
        capability_status=IdentityProviderCapability.UNAVAILABLE,
    )

    return [openai, gptunnel, specialized]


def get_provider_definition(
    settings: Settings, provider_code: str | None = None
) -> IdentityProviderDefinition:
    code = (provider_code or settings.image_generation_provider or "openai_images").strip().lower()
    if code == "gptunnel":
        code = "gptunnel_images"
    registry = build_identity_provider_registry(settings)
    for entry in registry:
        if entry.provider_code == code:
            return entry
    # Default to openai entry for unknown codes (still no secrets).
    return registry[0]


def serialize_registry_safe(settings: Settings) -> list[dict]:
    """JSON-safe registry — never includes credentials."""
    return [
        e.model_dump(mode="json")
        for e in build_identity_provider_registry(settings)
    ]
