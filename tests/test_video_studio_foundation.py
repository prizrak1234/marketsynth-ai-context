"""Video Studio VS.1 foundation + VS.2 single-clip API (no paid calls in tests)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.media_generation.gateway import (
    GatewayCreateResult,
    GatewayInvokeStatus,
    GatewayModality,
    GatewayPollResult,
)
from app.media_generation.video_readiness import SMOKE_PATH, image_to_video_live_verified, write_smoke_success
from app.media_generation.video_router import build_video_router
from app.media_generation.video_single_clip_service import VideoSingleClipService

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def owner_headers(database_url: str) -> dict[str, str]:
    import asyncio
    import random

    from app.schemas.contracts import UserRole
    from app.schemas.crud import UserCreate
    from app.services.auth import AuthService
    from app.services.users_service import UserService
    from tests.conftest import _init_database_schema

    async def _go() -> dict[str, str]:
        await _init_database_schema()
        from app.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            user_service = UserService(session)
            auth_service = AuthService(session)
            user = await user_service.create(
                UserCreate(
                    telegram_id=random.randint(1_000_000, 9_999_999),
                    display_name="Owner",
                    role=UserRole.OWNER,
                ),
            )
            created = await auth_service.create_api_key(user.id, "pytest-owner")
            return {"Authorization": f"Bearer {created.plain_key}"}

    return asyncio.run(_go())


def test_smoke_file_defaults_unverified() -> None:
    assert image_to_video_live_verified() is False


def test_write_smoke_success_flips_verified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "video_i2v_live_smoke.json"
    monkeypatch.setattr("app.media_generation.video_readiness.SMOKE_PATH", target)
    write_smoke_success(
        provider_code="gptunnel_creativelab",
        model="glabs-veo-3-1-fast",
        cost_units="49",
        checksum_sha256="abc",
        result_asset_hint="abc",
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["image_to_video_live_verified"] is True


def test_video_router_quotes_without_connected_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIDEO_GENERATION_ENABLED", "false")
    get_settings.cache_clear()
    router = build_video_router(get_settings())
    bundle = router.quote(modality=GatewayModality.VIDEO)
    assert bundle.quotes
    assert all(not q.connected for q in bundle.quotes)


def test_video_router_connects_gptunnel_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIDEO_GENERATION_ENABLED", "true")
    monkeypatch.setenv("GPTUNNEL_API_KEY", "test-key")
    get_settings.cache_clear()
    router = build_video_router(get_settings())
    assert router.any_connected
    assert "gptunnel_creativelab" in router.connected_codes()


@pytest.mark.asyncio
async def test_single_clip_preview_blocked_without_live_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIDEO_GENERATION_ENABLED", "true")
    monkeypatch.setenv("GPTUNNEL_API_KEY", "test-key")
    get_settings.cache_clear()
    svc = VideoSingleClipService(get_settings())
    preview = svc.preview_text_to_video(brief="Slow pan over a calm SaaS dashboard UI.")
    assert preview.ready_to_generate is False
    assert preview.blocked_reason_ru
    assert preview.cost_quotes.recommendation_display_name


def test_health_runtime_exposes_router(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPTUNNEL_API_KEY", "test-key")
    monkeypatch.setenv("VIDEO_GENERATION_ENABLED", "true")
    get_settings.cache_clear()
    resp = client.get("/health/runtime")
    assert resp.status_code == 200
    body = resp.json()
    va = body["content_factory_integrations"]["video_aggregator"]
    assert va["image_to_video_live_verified"] is False
    assert "video_client_connected" in va
    gateway = body["content_factory_integrations"]["commercial_pipeline"]["ports"]["image_video_gateway"]
    assert gateway["video_router"]["port"] == "VideoRouter"


def test_video_smoke_execute_requires_explicit_confirmation(
    client: TestClient,
    owner_headers: dict[str, str],
) -> None:
    resp = client.post(
        "/media-generation/video-smoke/execute",
        json={"explicit_confirmation": False},
        headers=owner_headers,
    )
    assert resp.status_code == 400


@pytest.mark.skip(reason="legacy expert single-clip HTTP path excluded from VS.2A commercial slice")
@pytest.mark.asyncio
async def test_single_clip_generate_mocked(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    smoke = tmp_path / "smoke.json"
    smoke.write_text(
        json.dumps(
            {
                "image_to_video_live_verified": True,
                "status": "LIVE_VERIFIED",
                "checksum_sha256": "abc123",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.media_generation.video_readiness.SMOKE_PATH", smoke)
    monkeypatch.setenv("VIDEO_GENERATION_ENABLED", "true")
    monkeypatch.setenv("GPTUNNEL_API_KEY", "test-key")
    get_settings.cache_clear()

    async def fake_create(_request):
        return (
            "gptunnel_creativelab",
            GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id="task-1",
                paid_call_performed=True,
            ),
        )

    async def fake_poll(_code, _job):
        return GatewayPollResult(
            status=GatewayInvokeStatus.DONE,
            url="https://cdn.example.test/clip.mp4",
            mime="video/mp4",
            paid_call_performed=True,
        )

    with patch(
        "app.media_generation.video_single_clip_service.build_video_router"
    ) as build_mock:
        router = build_video_router(get_settings())
        router.create = fake_create  # type: ignore[method-assign]
        router.poll = fake_poll  # type: ignore[method-assign]
        build_mock.return_value = router

        preview = client.post(
            "/media-generation/video-studio/single-clip/preview",
            json={
                "mode": "text_to_video",
                "brief": "Product demo of a SaaS analytics dashboard.",
                "duration_seconds": 8,
                "aspect_ratio": "16:9",
            },
            headers=owner_headers,
        )
        assert preview.status_code == 200
        assert preview.json()["ready_to_generate"] is True

        gen = client.post(
            "/media-generation/video-studio/single-clip/generate",
            json={
                "mode": "text_to_video",
                "brief": "Product demo of a SaaS analytics dashboard.",
                "duration_seconds": 8,
                "aspect_ratio": "16:9",
                "approved": True,
            },
            headers=owner_headers,
        )
        assert gen.status_code == 200
        body = gen.json()
        assert body["status"] == "done"
        assert body["has_result_url"] is True


def test_real_smoke_file_in_repo_is_unverified_by_default() -> None:
    if SMOKE_PATH.is_file():
        data = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
        assert data.get("image_to_video_live_verified") is not True
