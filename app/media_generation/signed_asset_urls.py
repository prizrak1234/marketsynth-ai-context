"""Short-lived one-time HMAC signed URLs for provider fetch (no session cookies).

Opaque resource IDs — no filesystem paths in the public URL.
TTL hard-capped at 10 minutes. One-time consumption via Redis (in-memory fallback).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
PURPOSE_PROVIDER_FETCH = "provider_fetch"
MAX_TTL_SECONDS = 600  # 10 minutes hard cap (owner requirement)
MIN_TTL_SECONDS = 60
# Providers (GPTunnel/Veo) probe HEAD + multiple GETs from different edges.
# Keep short TTL; allow a small use budget instead of strict single GET.
DEFAULT_MAX_USES = 5

CAPABILITY_PROOF_FILES: frozenset[str] = frozenset(
    {
        "smoke_keyframe_road_static.png",
    }
)

# Process-local one-time fallback when Redis is unavailable (tests / single-worker).
_LOCAL_GRANTS: dict[str, dict[str, Any]] = {}
_LOCAL_USED: set[str] = set()  # exhausted jtis


class SignedUrlError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class SignedMediaGrant:
    absolute_url: str
    path: str
    expires_at: int
    ttl_seconds: int
    purpose: str
    jti: str
    one_time: bool = True
    max_uses: int = DEFAULT_MAX_USES


def _secret_bytes(settings: Settings) -> bytes:
    secret = settings.asset_signed_url_secret
    if secret is None or not secret.get_secret_value().strip():
        raise SignedUrlError("secret_missing", "ASSET_SIGNED_URL_SECRET is not configured")
    return secret.get_secret_value().strip().encode("utf-8")


def _clamp_ttl(settings: Settings, ttl_seconds: int | None) -> int:
    configured = int(settings.asset_signed_url_ttl_seconds)
    raw = int(ttl_seconds if ttl_seconds is not None else configured)
    return max(MIN_TTL_SECONDS, min(raw, MAX_TTL_SECONDS, configured, MAX_TTL_SECONDS))


def _signing_payload(*, jti: str, exp: int, purpose: str) -> bytes:
    return f"v2|{purpose}|{jti}|{exp}".encode("utf-8")


def sign(settings: Settings, *, jti: str, exp: int, purpose: str) -> str:
    return hmac.new(
        _secret_bytes(settings),
        _signing_payload(jti=jti, exp=exp, purpose=purpose),
        hashlib.sha256,
    ).hexdigest()


def mask_url(url: str) -> str:
    """Owner-safe display: keep host/path shape, redact query signature."""
    if not url:
        return ""
    if "?" not in url:
        return url
    base, query = url.split("?", 1)
    parts: list[str] = []
    for chunk in query.split("&"):
        if chunk.startswith("sig="):
            sig = chunk[4:]
            if len(sig) <= 8:
                parts.append("sig=********")
            else:
                parts.append(f"sig={sig[:4]}…{sig[-4:]}")
        elif chunk.startswith("exp="):
            parts.append(chunk)
        elif chunk.startswith("purpose="):
            parts.append(chunk)
        else:
            parts.append("…")
    return f"{base}?{'&'.join(parts)}"


async def _redis_set_grant(jti: str, payload: dict[str, Any], ttl: int) -> bool:
    try:
        from app.core.redis import get_redis

        redis = get_redis()
        key = f"signed_media:grant:{jti}"
        ok = await redis.set(key, json.dumps(payload), nx=True, ex=ttl)
        return bool(ok)
    except Exception:
        return False


_REDIS_TAKE_USE_LUA = """
local v = redis.call('GET', KEYS[1])
if not v then
  return nil
end
local uses = tonumber(string.match(v, '"uses_left"%s*:%s*(%d+)'))
if uses == nil then
  uses = 1
end
if uses < 1 then
  redis.call('DEL', KEYS[1])
  return nil
end
uses = uses - 1
local newv, n = string.gsub(v, '"uses_left"%s*:%s*%d+', '"uses_left":' .. uses, 1)
if n == 0 then
  newv = string.gsub(v, '}$', ',"uses_left":' .. uses .. '}', 1)
end
if uses < 1 then
  redis.call('DEL', KEYS[1])
else
  local ttl = redis.call('TTL', KEYS[1])
  if ttl > 0 then
    redis.call('SET', KEYS[1], newv, 'EX', ttl)
  else
    redis.call('SET', KEYS[1], newv)
  end
end
return v
"""


async def _redis_take_grant_use(jti: str) -> dict[str, Any] | None:
    """Atomically consume one use. Deletes grant when uses_left reaches 0."""
    try:
        from app.core.redis import get_redis

        redis = get_redis()
        key = f"signed_media:grant:{jti}"
        raw = await redis.eval(_REDIS_TAKE_USE_LUA, 1, key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def resolve_capability_proof_path(settings: Settings, filename: str) -> Path:
    if filename not in CAPABILITY_PROOF_FILES:
        raise SignedUrlError("not_allowlisted", "Resource is not allowlisted for signing")
    root = Path(settings.image_generation_storage_dir)
    if not root.is_absolute():
        root = REPO_ROOT / root
    path = (root / "capability_proof" / filename).resolve()
    allowed_root = (root / "capability_proof").resolve()
    if allowed_root not in path.parents and path.parent != allowed_root:
        raise SignedUrlError("path_escape", "Resolved path escapes allowlisted root")
    if not path.is_file():
        raise SignedUrlError("missing_file", "Allowlisted file is missing")
    return path


def _validate_sig_exp(
    settings: Settings,
    *,
    jti: str,
    exp: int,
    sig: str,
    purpose: str,
) -> None:
    if not settings.asset_signed_url_enabled:
        raise SignedUrlError("disabled", "Signed media URLs are disabled")
    now = int(time.time())
    if exp < now:
        raise SignedUrlError("expired", "Signed URL expired")
    if exp > now + MAX_TTL_SECONDS + 30:
        raise SignedUrlError("exp_invalid", "Signed URL expiry out of range")
    expected = sign(settings, jti=jti, exp=exp, purpose=purpose)
    if not hmac.compare_digest(expected, (sig or "").strip()):
        raise SignedUrlError("bad_signature", "Invalid signature")


async def peek_opaque_grant(
    settings: Settings,
    *,
    jti: str,
    exp: int,
    sig: str,
    purpose: str = PURPOSE_PROVIDER_FETCH,
) -> Path:
    """Validate signature/expiry for HEAD probes without consuming uses."""
    _validate_sig_exp(settings, jti=jti, exp=exp, sig=sig, purpose=purpose)
    if jti in _LOCAL_USED:
        raise SignedUrlError("already_used", "Signed URL already consumed")
    grant = _LOCAL_GRANTS.get(jti)
    if grant is None:
        try:
            from app.core.redis import get_redis

            raw = await get_redis().get(f"signed_media:grant:{jti}")
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                parsed = json.loads(raw)
                grant = parsed if isinstance(parsed, dict) else None
        except Exception:
            grant = None
    if grant is None:
        raise SignedUrlError("already_used", "Signed URL already consumed or unknown")
    if int(grant.get("exp") or 0) != exp:
        raise SignedUrlError("exp_mismatch", "Grant expiry mismatch")
    if str(grant.get("purpose") or "") != purpose:
        raise SignedUrlError("purpose_mismatch", "Grant purpose mismatch")
    return _resolve_grant_path(settings, grant, str(grant.get("filename") or ""))


async def mint_capability_proof_url(
    settings: Settings,
    *,
    filename: str = "smoke_keyframe_road_static.png",
    ttl_seconds: int | None = None,
    purpose: str = PURPOSE_PROVIDER_FETCH,
    max_uses: int = DEFAULT_MAX_USES,
) -> SignedMediaGrant:
    if not settings.asset_signed_url_enabled:
        raise SignedUrlError("disabled", "Signed media URLs are disabled")
    if purpose != PURPOSE_PROVIDER_FETCH:
        raise SignedUrlError("bad_purpose", "Unsupported signing purpose")
    resolve_capability_proof_path(settings, filename)
    ttl = _clamp_ttl(settings, ttl_seconds)
    uses = max(1, min(int(max_uses), 10))
    exp = int(time.time()) + ttl
    jti = secrets.token_urlsafe(18)
    sig = sign(settings, jti=jti, exp=exp, purpose=purpose)
    base = (settings.public_backend_url or "").rstrip("/")
    if not base:
        raise SignedUrlError(
            "public_backend_missing",
            "PUBLIC_BACKEND_URL is required to mint an absolute signed URL",
        )
    # Opaque path — no filename, no storage directory.
    rel = f"/signed-media/o/{jti}"
    query = urlencode({"exp": str(exp), "purpose": purpose, "sig": sig})
    absolute = f"{base}{rel}?{query}"

    grant_payload = {
        "filename": filename,
        "purpose": purpose,
        "exp": exp,
        "created_at": int(time.time()),
        "uses_left": uses,
        "max_uses": uses,
    }
    stored = await _redis_set_grant(jti, grant_payload, ttl)
    if not stored:
        _LOCAL_GRANTS[jti] = dict(grant_payload)

    return SignedMediaGrant(
        absolute_url=absolute,
        path=rel,
        expires_at=exp,
        ttl_seconds=ttl,
        purpose=purpose,
        jti=jti,
        one_time=uses == 1,
        max_uses=uses,
    )


async def consume_opaque_grant(
    settings: Settings,
    *,
    jti: str,
    exp: int,
    sig: str,
    purpose: str = PURPOSE_PROVIDER_FETCH,
) -> Path:
    _validate_sig_exp(settings, jti=jti, exp=exp, sig=sig, purpose=purpose)
    if jti in _LOCAL_USED:
        raise SignedUrlError("already_used", "Signed URL already consumed")

    grant = await _redis_take_grant_use(jti)
    if grant is None:
        local = _LOCAL_GRANTS.get(jti)
        if local is None:
            raise SignedUrlError("already_used", "Signed URL already consumed or unknown")
        uses_left = int(local.get("uses_left") or 0)
        if uses_left < 1:
            _LOCAL_GRANTS.pop(jti, None)
            _LOCAL_USED.add(jti)
            raise SignedUrlError("already_used", "Signed URL already consumed or unknown")
        local["uses_left"] = uses_left - 1
        grant = dict(local)
        if local["uses_left"] < 1:
            _LOCAL_GRANTS.pop(jti, None)
            _LOCAL_USED.add(jti)

    if int(grant.get("exp") or 0) != exp:
        raise SignedUrlError("exp_mismatch", "Grant expiry mismatch")
    if str(grant.get("purpose") or "") != purpose:
        raise SignedUrlError("purpose_mismatch", "Grant purpose mismatch")
    filename = str(grant.get("filename") or "")
    return _resolve_grant_path(settings, grant, filename)


def _resolve_grant_path(settings: Settings, grant: dict[str, Any], filename: str) -> Path:
    kind = str(grant.get("grant_kind") or "capability_proof")
    if kind == "generated_visual_asset":
        raw = str(grant.get("content_path") or "")
        path = Path(raw)
        if not raw or not path.is_file():
            raise SignedUrlError("missing_file", "Asset file missing for signed grant")
        return path
    return resolve_capability_proof_path(settings, filename)


async def mint_generated_visual_asset_url(
    settings: Settings,
    *,
    asset_id: UUID,
    content_path: str,
    ttl_seconds: int | None = None,
    purpose: str = PURPOSE_PROVIDER_FETCH,
    max_uses: int = DEFAULT_MAX_USES,
) -> SignedMediaGrant:
    """Mint short-lived provider-fetch URL for an owner asset file (never permanent public URL)."""
    from uuid import UUID as _UUID

    if not settings.asset_signed_url_enabled:
        raise SignedUrlError("disabled", "Signed media URLs are disabled")
    if purpose != PURPOSE_PROVIDER_FETCH:
        raise SignedUrlError("bad_purpose", "Unsupported signing purpose")
    path = Path(content_path)
    if not path.is_file():
        raise SignedUrlError("missing_file", "Asset file missing")
    ttl = _clamp_ttl(settings, ttl_seconds)
    uses = max(1, min(int(max_uses), 10))
    exp = int(time.time()) + ttl
    jti = secrets.token_urlsafe(18)
    sig = sign(settings, jti=jti, exp=exp, purpose=purpose)
    base = (settings.public_backend_url or "").rstrip("/")
    if not base:
        raise SignedUrlError(
            "public_backend_missing",
            "PUBLIC_BACKEND_URL is required to mint an absolute signed URL",
        )
    rel = f"/signed-media/o/{jti}"
    query = urlencode({"exp": str(exp), "purpose": purpose, "sig": sig})
    absolute = f"{base}{rel}?{query}"
    grant_payload = {
        "grant_kind": "generated_visual_asset",
        "asset_id": str(_UUID(str(asset_id))),
        "content_path": str(path.resolve()),
        "purpose": purpose,
        "exp": exp,
        "created_at": int(time.time()),
        "uses_left": uses,
        "max_uses": uses,
    }
    stored = await _redis_set_grant(jti, grant_payload, ttl)
    if not stored:
        _LOCAL_GRANTS[jti] = dict(grant_payload)
    return SignedMediaGrant(
        absolute_url=absolute,
        path=rel,
        expires_at=exp,
        ttl_seconds=ttl,
        purpose=purpose,
        jti=jti,
        one_time=uses == 1,
        max_uses=uses,
    )


def signed_url_readiness(settings: Settings) -> dict[str, object]:
    secret_ok = bool(
        settings.asset_signed_url_secret
        and settings.asset_signed_url_secret.get_secret_value().strip()
    )
    public_ok = bool((settings.public_backend_url or "").strip())
    public_url = (settings.public_backend_url or "").strip()
    localhostish = any(
        h in public_url.lower()
        for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")
    )
    proof_ok = False
    try:
        resolve_capability_proof_path(settings, "smoke_keyframe_road_static.png")
        proof_ok = True
    except SignedUrlError:
        proof_ok = False
    return {
        "enabled": bool(settings.asset_signed_url_enabled),
        "secret_configured": secret_ok,
        "public_backend_url_configured": public_ok,
        "public_backend_looks_local": localhostish,
        "ttl_seconds_max": MAX_TTL_SECONDS,
        "ttl_seconds_configured": min(int(settings.asset_signed_url_ttl_seconds), MAX_TTL_SECONDS),
        "one_time": True,
        "opaque_paths": True,
        "capability_proof_present": proof_ok,
        "ready_to_mint": bool(
            settings.asset_signed_url_enabled and secret_ok and public_ok and proof_ok
        ),
        "note": (
            "GPTunnel must GET the signed URL from the public internet; "
            "localhost PUBLIC_BACKEND_URL will fail aggregator fetch."
        ),
    }


def build_video_smoke_preview(
    settings: Settings,
    *,
    grant: SignedMediaGrant | None,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    """Owner-facing preview for the next confirmation step (no paid call)."""
    from app.media_generation.video_aggregator_status import video_aggregator_public_status

    video = video_aggregator_public_status(settings)
    masked = mask_url(grant.absolute_url) if grant else None
    return {
        "paid_smoke": "not_run",
        "awaiting": "owner_explicit_confirmation",
        "blocked_reason": blocked_reason,
        "aggregator": video.get("code"),
        "model": video.get("selected_pilot_model") or "glabs-veo-3-1-fast",
        "operation": "image_to_video",
        "duration_target_seconds": "3-5 (provider default for selected model)",
        "aspect_ratio": "16:9",
        "resolution": "provider_default (not separately declared for Veo Fast)",
        "estimated_max_cost_units": video.get("estimated_pilot_cost_units") or "49",
        "keyframe": "capability_proof smoke keyframe (opaque signed URL)",
        "signed_url_masked": masked,
        "signed_url_ttl_seconds": grant.ttl_seconds if grant else None,
        "signed_url_expires_at": grant.expires_at if grant else None,
        "signed_url_one_time": True if grant else None,
        "signed_url_lists_internal_paths": False,
        "retries": 0,
        "tls_bypass": False,
    }
