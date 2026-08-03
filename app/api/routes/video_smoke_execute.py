"""Owner-paid video i2v smoke — explicit_confirmation gate only."""

from __future__ import annotations

import hashlib
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies.auth import require_role
from app.core.config import Settings, get_settings
from app.core.security import sanitize_payload
from app.db.models.user import UserTable
from app.media_generation.gateway import GatewayCreateRequest, GatewayInvokeStatus, GatewayModality
from app.media_generation.signed_asset_urls import SignedUrlError, mint_capability_proof_url
from app.media_generation.video_readiness import write_smoke_success
from app.media_generation.video_router import build_video_router
from app.media_generation.video_smoke_package import PILOT_AR, PILOT_COST_UNITS
from app.schemas.contracts import UserRole

router = APIRouter(prefix="/media-generation", tags=["media-generation"])


class VideoSmokeExecuteRequest(BaseModel):
    explicit_confirmation: bool = Field(
        ...,
        description="Must be true after owner reviewed preview package.",
    )


@router.post("/video-smoke/execute")
async def execute_video_smoke(
    body: VideoSmokeExecuteRequest,
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> dict[str, Any]:
    """Run one paid GPTunnel i2v smoke. Writes data/audits/video_i2v_live_smoke.json on success."""
    _ = current_user
    if not body.explicit_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="explicit_confirmation_required",
        )
    if not settings.video_generation_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video_generation_disabled",
        )
    router = build_video_router(settings)
    if not router.any_connected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video_router_no_adapter",
        )

    try:
        grant = await mint_capability_proof_url(settings, ttl_seconds=600)
    except SignedUrlError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.code) from exc

    prompt = sanitize_payload(
        "Static camera. A single technical road construction machine slowly "
        "rolls forward a short distance on an empty road. No people, no text, "
        "no logos, no extra vehicles. Photorealistic, natural daylight."
    )
    request = GatewayCreateRequest(
        modality=GatewayModality.VIDEO,
        model=settings.gptunnel_video_model,
        prompt=prompt,
        aspect_ratio=PILOT_AR,
        images=[grant.absolute_url],
        metadata={"purpose": "owner_paid_smoke"},
    )
    provider_code, created = await router.create(request)
    if created.status != GatewayInvokeStatus.QUEUED or not created.job_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=created.detail_code or "create_failed",
        )

    polled = await router.poll(provider_code, created.job_id)
    if polled.status != GatewayInvokeStatus.DONE or not polled.url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=polled.detail_code or "poll_failed",
        )

    checksum: str | None = None
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        dl = await client.get(polled.url)
        if dl.status_code == 200:
            checksum = hashlib.sha256(dl.content).hexdigest()
            if not dl.headers.get("content-type", "").startswith("video/"):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="smoke_result_not_video",
                )

    smoke = write_smoke_success(
        provider_code=provider_code,
        model=settings.gptunnel_video_model,
        cost_units=PILOT_COST_UNITS,
        checksum_sha256=checksum,
        result_asset_hint=checksum[:16] if checksum else None,
    )
    return {
        "status": "LIVE_VERIFIED",
        "paid_smoke_performed": True,
        "provider_code": provider_code,
        "job_id": created.job_id,
        "result_mime": polled.mime,
        "checksum_sha256_prefix": checksum[:16] if checksum else None,
        "live_smoke": smoke,
        "note": "Create Video UI gate will unlock via /health/runtime image_to_video_live_verified=true.",
    }
