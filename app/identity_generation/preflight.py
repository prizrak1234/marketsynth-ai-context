"""H2.8E — preflight readiness gate for person_identity_preservation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.identity_generation.errors import identity_error_message
from app.identity_generation.registry import get_provider_definition
from app.schemas.contracts import (
    IdentityGenerationReadiness,
    IdentityPreflightCondition,
    IdentityProviderCapability,
    IdentityReferenceManifest,
    ReferenceQualityStatus,
    VisualExecutionMode,
)


def evaluate_identity_preflight(
    *,
    settings: Settings,
    owner_id: UUID,
    reference_set: Any | None,
    reference_rows: list[Any],
    primary_reference_id: UUID | None,
    consent: bool,
    prompt: str,
    identity_profile_present: bool,
    paid_approval_granted: bool = False,
    manifest: IdentityReferenceManifest | None = None,
    estimated_calls: int = 1,
) -> IdentityGenerationReadiness:
    """Return typed readiness. Blocking conditions stop provider calls."""
    provider = get_provider_definition(settings)
    conditions: list[IdentityPreflightCondition] = []

    def add(code: str, *, ok: bool, blocking: bool = True) -> None:
        conditions.append(
            IdentityPreflightCondition(
                code=code,
                blocking=blocking and not ok,
                safe_message=identity_error_message(code),
                ok=ok,
            )
        )

    add("credentials_missing", ok=bool(provider.configured))
    mode_ok = VisualExecutionMode.PERSON_IDENTITY_PRESERVATION in provider.supported_modes
    # GPTunnel: not in supported_modes for identity
    if provider.provider_code == "gptunnel_images":
        mode_ok = False
    add("identity_mode_not_supported", ok=mode_ok)

    set_ok = reference_set is not None and getattr(reference_set, "owner_id", None) == owner_id
    add("reference_set_required", ok=set_ok)
    if reference_set is not None and getattr(reference_set, "owner_id", None) != owner_id:
        conditions.append(
            IdentityPreflightCondition(
                code="owner_mismatch",
                blocking=True,
                safe_message=identity_error_message("owner_mismatch"),
                ok=False,
            )
        )

    accepted = [
        r
        for r in reference_rows
        if str(getattr(r, "quality_status", "")).endswith("suitable")
        or getattr(r, "quality_status", None) == ReferenceQualityStatus.SUITABLE
        or getattr(r, "quality_status", None) == ReferenceQualityStatus.LIMITED
        or str(getattr(getattr(r, "quality_status", None), "value", getattr(r, "quality_status", "")))
        in {"suitable", "limited", "pending"}
    ]
    add("reference_set_empty", ok=len(accepted) >= 1 or len(reference_rows) >= 1)
    add("consent_required", ok=bool(consent))
    add("primary_reference_required", ok=primary_reference_id is not None)
    add("identity_profile_required", ok=bool(identity_profile_present))
    prompt_ok = len((prompt or "").strip()) >= 8
    add("prompt_insufficient", ok=prompt_ok)

    if provider.approval_required and not paid_approval_granted:
        # Soft block for qualification; product generate may still use separate path
        conditions.append(
            IdentityPreflightCondition(
                code="paid_approval_required",
                blocking=False,
                safe_message=identity_error_message("paid_approval_required"),
                ok=False,
            )
        )

    blocking = [c for c in conditions if c.blocking]
    ready = len(blocking) == 0 and bool(provider.enabled or provider.configured)

    uploaded = len(reference_rows)
    selected_identity = (
        len(manifest.identity_reference_ids) if manifest else 0
    )
    selected_style = (
        (len(manifest.style_reference_ids) + len(manifest.appearance_reference_ids))
        if manifest
        else 0
    )
    will_receive = (
        manifest.references_provider_received_count
        if manifest
        else min(1, selected_identity or (1 if primary_reference_id else 0))
    )

    if ready and will_receive <= 1 and selected_identity > 1:
        detail = identity_error_message("selected_but_not_transmitted")
        summary = (
            f"Готово к тестовой генерации. Провайдер: {provider.provider_code}. "
            f"Передаётся: {will_receive} основной референс."
        )
        lines = [
            summary,
            detail,
            f"Загружено: {uploaded}. Для внешности выбрано: {selected_identity}. "
            f"Для стиля выбрано: {selected_style}.",
        ]
    elif not mode_ok:
        summary = identity_error_message("identity_mode_not_supported")
        lines = [summary]
        ready = False
    elif blocking:
        summary = blocking[0].safe_message
        lines = [c.safe_message for c in blocking]
        ready = False
    else:
        summary = (
            f"Готово к генерации. Провайдер: {provider.provider_code}. "
            f"Режим: сохранение внешности."
        )
        lines = [summary]

    mock_or_real = "mock" if (settings.image_generation_provider or "").lower() == "mock" else "real"
    capability = provider.capability_status
    if capability == IdentityProviderCapability.UNVERIFIED:
        capability = IdentityProviderCapability.UNKNOWN

    return IdentityGenerationReadiness(
        ready=ready and mode_ok,
        provider=provider.provider_code,
        provider_definition=provider,
        requested_mode=VisualExecutionMode.PERSON_IDENTITY_PRESERVATION,
        capability_status=capability,
        uploaded_references=uploaded,
        selected_identity_references=selected_identity,
        selected_style_references=selected_style,
        actual_provider_input_capacity=int(provider.maximum_identity_images),
        references_provider_will_receive=will_receive,
        blocking_conditions=conditions,
        paid_approval_required=bool(provider.approval_required),
        paid_approval_granted=paid_approval_granted,
        estimated_provider_calls=estimated_calls if ready else 0,
        mock_or_real=mock_or_real,
        safe_summary=summary,
        safe_detail_lines=lines,
    )
