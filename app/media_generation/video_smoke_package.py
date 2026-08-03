"""Commercial video smoke package builder — preview only, never calls GPTunnel."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.media_generation.signed_asset_urls import (
    SignedMediaGrant,
    build_video_smoke_preview,
    mask_url,
    signed_url_readiness,
)

PILOT_MODEL = "glabs-veo-3-1-fast"
PILOT_COST_UNITS = "49"
PILOT_AR = "16:9"
# Official CreativeLab FAQ: Veo family produces ~8s clips; Fast page does not
# declare FPS. Mark unverified fields explicitly.
PILOT_DURATION = {
    "target_seconds": "3-5 preferred for smoke",
    "provider_family_hint_seconds": 8,
    "source": "docs.gptunnel.ru/creative-lab/about (Veo-3 family) + Veo-3.1 Fast page",
    "live_verified": False,
}
PILOT_RESOLUTION = {
    "declared": "provider_default",
    "family_hint": "720p/1080p mentioned for Veo-3/Pro in FAQ; Fast not separately specified",
    "live_verified": False,
}
PILOT_FPS = {
    "declared": None,
    "live_verified": False,
    "note": "FPS not in CreativeLab Veo-3.1 Fast contract — treat as provider_default",
}


def build_create_payload(*, image_url: str | None, prompt: str, ar: str = PILOT_AR) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": PILOT_MODEL,
        "prompt": prompt,
        "ar": ar,
    }
    if image_url:
        payload["images"] = [image_url]
    return payload


def build_commercial_smoke_package(
    settings: Settings,
    *,
    grant: SignedMediaGrant | None = None,
    blocked_reason: str | None = None,
    include_unmasked_url_for_internal: bool = False,
) -> dict[str, Any]:
    """Full owner package for approval gate. Paid call not performed here."""
    readiness = signed_url_readiness(settings)
    base_preview = build_video_smoke_preview(
        settings,
        grant=grant,
        blocked_reason=blocked_reason,
    )
    prompt = (
        "Static camera. A single technical road construction machine slowly "
        "rolls forward a short distance on an empty road. No people, no text, "
        "no logos, no extra vehicles. Photorealistic, natural daylight."
    )
    image_url = grant.absolute_url if grant else None
    payload = build_create_payload(image_url=image_url, prompt=prompt)
    # Never persist/log unmasked URL unless explicitly requested for minting step.
    payload_for_owner = dict(payload)
    if image_url:
        payload_for_owner["images"] = [mask_url(image_url)]

    return {
        "status": "READY_FOR_OWNER_EXPLICIT_CONFIRMATION",
        "paid_smoke": "not_run",
        "commercial_gate": {
            "flow": [
                "TZ",
                "analysis",
                "keyframe",
                "signed_url",
                "preview",
                "owner_approval",
                "1_paid_generation",
                "QA",
                "repair_if_needed",
            ],
            "spend_only_after": "explicit_confirmation=true",
        },
        "aggregator": {
            "code": "gptunnel_creativelab",
            "endpoint_create": "POST /v1/media/create",
            "endpoint_result": "POST /v1/media/result",
            "base_url_safe": (settings.gptunnel_base_url or "https://gptunnel.ru/v1").rstrip("/"),
        },
        "model": {
            "id": PILOT_MODEL,
            "operation": "image_to_video",
            "estimated_max_cost_units": PILOT_COST_UNITS,
            "cost_live_verified": False,
            "catalog_source": "GPTunnel media/models",
        },
        "video_expectations": {
            "duration": PILOT_DURATION,
            "aspect_ratio": PILOT_AR,
            "resolution": PILOT_RESOLUTION,
            "fps": PILOT_FPS,
            "result_mime_expected": "video/mp4",
            "camera": "static",
            "motion": "single slow forward machine move",
        },
        "execution_limits": {
            "attempt_limit": 1,
            "hidden_retries": 0,
            "tls_bypass": False,
            "silent_image_fallback_allowed": False,
            "timeout_poll_max_iterations": 40,
            "poll_interval_seconds": 1.5,
        },
        "signed_url": {
            "masked": mask_url(image_url) if image_url else None,
            "ttl_seconds": grant.ttl_seconds if grant else None,
            "expires_at": grant.expires_at if grant else None,
            "one_time": True,
            "opaque_path": True,
            "lists_internal_paths": False,
            "absolute_url_unmasked": image_url if include_unmasked_url_for_internal else None,
            "readiness": readiness,
        },
        "keyframe": {
            "source": "capability_proof",
            "logical_name": "smoke_keyframe_road_static.png",
            "served_as": "opaque one-time signed URL",
        },
        "request_payload_masked": payload_for_owner,
        "result_contract": {
            "expect_status_done": True,
            "expect_url_mp4": True,
            "persist_local_asset": True,
            "checksum_sha256": True,
            "fail_if_image_mime": True,
        },
        "blocked_reason": blocked_reason or base_preview.get("blocked_reason"),
        "confirmation_phrase_required": "explicit_confirmation=true",
        "confirmation_note": (
            "Reply with explicit_confirmation=true only after reviewing model, cost, "
            "duration, resolution/FPS caveats, attempt limit, and masked payload. "
            "Marketsynth will not start paid generation without that confirmation."
        ),
    }
