"""Owner preview for upcoming video smoke — no paid generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import require_role
from app.core.config import Settings, get_settings
from app.db.models.user import UserTable
from app.media_generation.signed_asset_urls import SignedUrlError, mint_capability_proof_url
from app.media_generation.video_smoke_package import build_commercial_smoke_package
from app.schemas.contracts import UserRole

router = APIRouter(prefix="/media-generation", tags=["media-generation"])


@router.post("/video-smoke/preview")
async def preview_video_smoke(
    settings: Settings = Depends(get_settings),
    current_user: UserTable = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> dict:
    """Mint a short-lived one-time signed keyframe URL and return commercial package.

    Does **not** call GPTunnel. Does **not** spend credits.
    """
    _ = current_user
    grant = None
    blocked: str | None = None
    try:
        grant = await mint_capability_proof_url(settings, ttl_seconds=600)
        package = build_commercial_smoke_package(settings, grant=grant)
        if package["signed_url"]["readiness"].get("public_backend_looks_local"):
            package["blocked_reason"] = (
                "public_backend_looks_local_may_fail_aggregator_fetch"
            )
        return package
    except SignedUrlError as exc:
        blocked = exc.code
        package = build_commercial_smoke_package(
            settings,
            grant=None,
            blocked_reason=blocked,
        )
        if exc.code in {"public_backend_missing", "disabled", "secret_missing", "missing_file"}:
            return package
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.code) from exc
