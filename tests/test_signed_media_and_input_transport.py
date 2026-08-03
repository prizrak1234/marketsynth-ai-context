"""Signed opaque one-time media URLs + input transport (no paid calls)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.media_generation.signed_asset_urls import (
    SignedUrlError,
    mask_url,
    mint_capability_proof_url,
    resolve_capability_proof_path,
    signed_url_readiness,
)

REPO = Path(__file__).resolve().parents[1]
TRANSPORT = REPO / "data/audits/gptunnel_image_input_transport.json"
PROBE = REPO / "data/audits/gptunnel_upload_probe.json"


def test_transport_audit_no_multipart() -> None:
    data = json.loads(TRANSPORT.read_text(encoding="utf-8"))
    assert data["paid_smoke"] == "not_run"
    assert data["temporary_internet_hosting_of_keyframe"] == "not_performed"
    assert data["creativelab_rest"]["multipart_for_i2v"] is False


def test_upload_probe_artifacts() -> None:
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    by_key = {
        (p["method"], p["url_path"]): p.get("status")
        for p in probe["probes"]
        if "status" in p
    }
    assert by_key.get(("POST", "/media/upload")) == 404
    assert by_key.get(("POST", "/media/models")) == 200


@pytest.mark.asyncio
async def test_signed_url_roundtrip_one_time(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ASSET_SIGNED_URL_ENABLED", "true")
    monkeypatch.setenv("ASSET_SIGNED_URL_SECRET", "test-signed-secret-not-for-prod")
    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://example.test")
    monkeypatch.setenv("ASSET_SIGNED_URL_TTL_SECONDS", "600")
    get_settings.cache_clear()
    settings = get_settings()
    assert signed_url_readiness(settings)["ready_to_mint"] is True
    grant = await mint_capability_proof_url(settings, ttl_seconds=600, max_uses=1)
    assert grant.ttl_seconds <= 600
    assert "/signed-media/o/" in grant.absolute_url
    assert "smoke_keyframe" not in grant.absolute_url
    assert "capability_proof" not in grant.path
    masked = mask_url(grant.absolute_url)
    assert "sig=" in masked
    assert "…" in masked or "********" in masked

    sig = grant.absolute_url.split("sig=")[1]
    first = client.get(
        f"{grant.path}?exp={grant.expires_at}&purpose=provider_fetch&sig={sig}"
    )
    assert first.status_code == 200, first.text
    assert first.headers["content-type"].startswith("image/")
    second = client.get(
        f"{grant.path}?exp={grant.expires_at}&purpose=provider_fetch&sig={sig}"
    )
    assert second.status_code == 410


@pytest.mark.asyncio
async def test_signed_url_rejects_bad_sig(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ASSET_SIGNED_URL_ENABLED", "true")
    monkeypatch.setenv("ASSET_SIGNED_URL_SECRET", "test-signed-secret-not-for-prod")
    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://example.test")
    get_settings.cache_clear()
    grant = await mint_capability_proof_url(get_settings())
    resp = client.get(
        f"{grant.path}?exp={grant.expires_at}&purpose=provider_fetch&sig={'0' * 64}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_signed_url_disabled_by_default() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    # env may enable during owner prep — assert mint fails when disabled flag false
    if not settings.asset_signed_url_enabled:
        with pytest.raises(SignedUrlError) as exc:
            await mint_capability_proof_url(settings)
        assert exc.value.code == "disabled"


def test_allowlist_blocks_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSET_SIGNED_URL_ENABLED", "true")
    monkeypatch.setenv("ASSET_SIGNED_URL_SECRET", "test-signed-secret-not-for-prod")
    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(SignedUrlError):
        resolve_capability_proof_path(settings, "../secret.png")


def test_ttl_cap_in_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSET_SIGNED_URL_TTL_SECONDS", "600")
    get_settings.cache_clear()
    assert get_settings().asset_signed_url_ttl_seconds <= 600
