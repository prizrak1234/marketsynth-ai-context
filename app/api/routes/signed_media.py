"""Unauthenticated opaque short-lived signed media delivery for provider fetch."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.media_generation.signed_asset_urls import (
    PURPOSE_PROVIDER_FETCH,
    SignedUrlError,
    consume_opaque_grant,
    peek_opaque_grant,
)

router = APIRouter(prefix="/signed-media", tags=["signed-media"])


def _map_err(exc: SignedUrlError) -> HTTPException:
    code = status.HTTP_403_FORBIDDEN
    if exc.code in {"disabled", "missing_file", "not_allowlisted"}:
        code = status.HTTP_404_NOT_FOUND
    if exc.code == "already_used":
        code = status.HTTP_410_GONE
    return HTTPException(status_code=code, detail=exc.code)


def _mime_for(path: Path) -> str:
    mime = "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif path.suffix.lower() == ".webp":
        mime = "image/webp"
    return mime


@router.head("/o/{jti}")
async def head_opaque_signed_media(
    jti: str,
    exp: int = Query(..., ge=1),
    sig: str = Query(..., min_length=32, max_length=128),
    purpose: str = Query(default=PURPOSE_PROVIDER_FETCH, max_length=64),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Providers probe with HEAD — validate without consuming GET budget."""
    try:
        path = await peek_opaque_grant(
            settings,
            jti=jti,
            exp=exp,
            sig=sig,
            purpose=purpose,
        )
    except SignedUrlError as exc:
        raise _map_err(exc) from exc
    mime = _mime_for(path)
    size = path.stat().st_size
    return Response(
        status_code=200,
        headers={
            "Content-Type": mime,
            "Content-Length": str(size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
        },
    )


@router.get("/o/{jti}")
async def get_opaque_signed_media(
    jti: str,
    exp: int = Query(..., ge=1),
    sig: str = Query(..., min_length=32, max_length=128),
    purpose: str = Query(default=PURPOSE_PROVIDER_FETCH, max_length=64),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    try:
        path = await consume_opaque_grant(
            settings,
            jti=jti,
            exp=exp,
            sig=sig,
            purpose=purpose,
        )
    except SignedUrlError as exc:
        raise _map_err(exc) from exc

    mime = _mime_for(path)
    # Filename is generic — do not leak storage layout.
    return FileResponse(path, media_type=mime, filename="keyframe.png")
