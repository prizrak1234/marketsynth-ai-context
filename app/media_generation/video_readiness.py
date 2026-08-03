"""Video i2v live smoke audit — source of truth for image_to_video_live_verified."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_PATH = REPO_ROOT / "data/audits/video_i2v_live_smoke.json"


def _load_smoke() -> dict[str, Any]:
    if not SMOKE_PATH.is_file():
        return {}
    try:
        data = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def image_to_video_live_verified(settings: object | None = None) -> bool:
    from app.core.config import Settings, get_settings
    from app.media_generation.gptunnel_video_gateway import try_build_gptunnel_video_gateway

    cfg: Settings = settings if isinstance(settings, Settings) else get_settings()  # type: ignore[assignment]
    if not cfg.video_generation_enabled:
        return False
    if try_build_gptunnel_video_gateway(cfg) is None:
        return False
    smoke = _load_smoke()
    if smoke.get("image_to_video_live_verified") is not True:
        return False
    if not smoke.get("checksum_sha256"):
        return False
    return True


def paid_smoke_status() -> str:
    smoke = _load_smoke()
    if smoke.get("image_to_video_live_verified") is True:
        return "LIVE_VERIFIED"
    return str(smoke.get("status") or "AWAITING_OWNER_EXPLICIT_CONFIRMATION")


def smoke_public_summary() -> dict[str, Any]:
    smoke = _load_smoke()
    return {
        "status": smoke.get("status"),
        "image_to_video_live_verified": smoke.get("image_to_video_live_verified") is True,
        "paid_smoke_performed": smoke.get("paid_smoke_performed") is True,
        "verified_at": smoke.get("verified_at"),
        "provider_code": smoke.get("provider_code"),
        "model": smoke.get("model"),
        "operation": smoke.get("operation"),
    }


def write_smoke_success(
    *,
    provider_code: str,
    model: str,
    cost_units: str | None,
    checksum_sha256: str | None,
    result_asset_hint: str | None,
) -> dict[str, Any]:
    from datetime import UTC, datetime

    payload = {
        "status": "LIVE_VERIFIED",
        "image_to_video_live_verified": True,
        "paid_smoke_performed": True,
        "verified_at": datetime.now(UTC).isoformat(),
        "provider_code": provider_code,
        "model": model,
        "operation": "image_to_video",
        "cost_units": cost_units,
        "result_asset_hint": result_asset_hint,
        "checksum_sha256": checksum_sha256,
        "note": "Owner explicit_confirmation paid smoke succeeded.",
    }
    SMOKE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
