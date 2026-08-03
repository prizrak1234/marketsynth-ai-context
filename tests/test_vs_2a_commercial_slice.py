"""VS.2A commercial vertical slice — preview, approval binding, idempotency, asset."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
from app.db.models.user_request import UserRequestTable
from app.db.models.video_clip_request import VideoClipRequestTable
from app.media_generation.gateway import (
    GatewayCreateResult,
    GatewayInvokeStatus,
    GatewayPollResult,
)
from app.media_generation.video_readiness import image_to_video_live_verified
from app.media_generation.video_router import build_video_router
from app.schemas.contracts import (
    GeneratedVisualAssetStatus,
    GeneratedVisualAssetType,
    GeneratedVisualGenerationMode,
    UserRequestStatus,
    VideoClipRequestStatus,
)
from fastapi.testclient import TestClient


@pytest.fixture
def owner_headers(database_url: str) -> dict[str, str]:
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
            created = await auth_service.create_api_key(user.id, "pytest-vs2a-owner")
            return {"Authorization": f"Bearer {created.plain_key}"}

    return asyncio.run(_go())


@pytest.fixture
def live_video_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    smoke = tmp_path / "smoke.json"
    smoke.write_text(
        json.dumps(
            {
                "image_to_video_live_verified": True,
                "checksum_sha256": "abc123",
                "status": "LIVE_VERIFIED",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.media_generation.video_readiness.SMOKE_PATH", smoke)
    monkeypatch.setenv("VIDEO_GENERATION_ENABLED", "true")
    monkeypatch.setenv("GPTUNNEL_API_KEY", "test-key")
    monkeypatch.setenv("ASSET_SIGNED_URL_ENABLED", "true")
    monkeypatch.setenv("ASSET_SIGNED_URL_SECRET", "test-signed-secret")
    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://example.test")
    get_settings.cache_clear()


def _seed_source_image(
    client: TestClient,
    headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    storage = tmp_path / "visuals"
    storage.mkdir()
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(storage))
    get_settings.cache_clear()

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    owner_id = UUID(me.json()["id"])

    async def _seed() -> str:
        from app.db.session import get_session_factory

        asset_id = uuid4()
        img = storage / f"{asset_id}.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 64)
        factory = get_session_factory()
        async with factory() as session:
            ur = UserRequestTable(
                owner_id=owner_id,
                text="Commercial slice test image",
                normalized_text="Commercial slice test image",
                status=UserRequestStatus.COMPLETED,
            )
            session.add(ur)
            await session.flush()
            session.add(
                GeneratedVisualAssetTable(
                    id=asset_id,
                    owner_id=owner_id,
                    user_request_id=ur.id,
                    skill_code="design.image_generation",
                    skill_version="1.0",
                    provider="mock",
                    generation_mode=GeneratedVisualGenerationMode.MOCK,
                    asset_type=GeneratedVisualAssetType.USER_RESULT,
                    prompt_summary="test",
                    mime_type="image/png",
                    content_path=str(img),
                    storage_uri=f"/generated-visual-assets/{asset_id}/content",
                    status=GeneratedVisualAssetStatus.SUCCEEDED,
                    user_accepted=True,
                    review_notes="vs2a_test_accepted",
                )
            )
            await session.commit()
            return str(asset_id)

    return asyncio.run(_seed())


def test_readiness_requires_config_and_checksum(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    smoke = tmp_path / "smoke.json"
    smoke.write_text(json.dumps({"image_to_video_live_verified": True}), encoding="utf-8")
    monkeypatch.setattr("app.media_generation.video_readiness.SMOKE_PATH", smoke)
    monkeypatch.setenv("VIDEO_GENERATION_ENABLED", "false")
    get_settings.cache_clear()
    assert image_to_video_live_verified() is False


def test_commercial_preview_persists_request(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_source_image(client, owner_headers, tmp_path, monkeypatch)
    resp = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Slow camera push-in over product dashboard",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clip_request_id"]
    payload = json.dumps(body)
    assert "gptunnel" not in payload.lower()
    assert "provider_code" not in payload


def test_generate_requires_approval(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_source_image(client, owner_headers, tmp_path, monkeypatch)
    preview = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Gentle parallax on hero image",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    clip_id = preview.json()["clip_request_id"]
    denied = client.post(
        f"/media-generation/video-clips/{clip_id}/generate",
        headers={**owner_headers, "Idempotency-Key": "deny-approval-001"},
        json={"approved": False},
    )
    assert denied.status_code == 400


def test_generate_idempotent_and_creates_video_asset(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_source_image(client, owner_headers, tmp_path, monkeypatch)
    preview = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Gentle parallax on hero image",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    clip_id = preview.json()["clip_request_id"]
    idem = "test-idem-vs2a-001"

    async def fake_create(_request):
        return (
            "gptunnel_creativelab",
            GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id="job-1",
                paid_call_performed=True,
            ),
        )

    async def fake_poll(_code, _job):
        return GatewayPollResult(
            status=GatewayInvokeStatus.DONE,
            url="https://example.test/fake.mp4",
            mime="video/mp4",
            paid_call_performed=True,
        )

    from app.media_generation.video_clip_download import VideoDownloadResult

    async def fake_download(_settings, *, url, mime_hint):
        _ = url, mime_hint
        return VideoDownloadResult(
            temp_path=tmp_path / "fake.mp4",
            mime="video/mp4",
            checksum_sha256="deadbeef",
            size_bytes=16,
        )

    fake_file = tmp_path / "fake.mp4"
    fake_file.write_bytes(b"fake-mp4-bytes")

    monkeypatch.setattr(
        "app.services.video_clip_commercial_service.download_provider_video_to_temp",
        fake_download,
    )
    monkeypatch.setattr(
        "app.services.video_clip_commercial_service.finalize_video_temp_file",
        lambda temp_path, storage_dir, asset_id: storage_dir / f"{asset_id}.mp4",
    )
    monkeypatch.setattr(
        "app.services.video_clip_commercial_service.probe_mp4_duration_seconds",
        lambda _path: 8.0,
    )

    def build_mock_router(settings):
        router = build_video_router(settings)
        router.create = fake_create  # type: ignore[method-assign]
        router.poll = fake_poll  # type: ignore[method-assign]
        return router

    with patch(
        "app.services.video_clip_commercial_service.build_video_router",
        side_effect=build_mock_router,
    ):
        headers = {**owner_headers, "Idempotency-Key": idem}
        gen1 = client.post(
            f"/media-generation/video-clips/{clip_id}/generate",
            headers=headers,
            json={"approved": True},
        )
        assert gen1.status_code == 200, gen1.text
        body1 = gen1.json()
        assert body1["result_asset_id"]
        assert body1["status"] == "succeeded"
        assert "provider_code" not in body1

        gen2 = client.post(
            f"/media-generation/video-clips/{clip_id}/generate",
            headers=headers,
            json={"approved": True},
        )
        assert gen2.status_code == 200
        assert gen2.json()["result_asset_id"] == body1["result_asset_id"]

    async def _load_row() -> VideoClipRequestTable:
        from app.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            row = await session.get(VideoClipRequestTable, UUID(clip_id))
            assert row is not None
            return row

    row = asyncio.run(_load_row())
    assert row.status == VideoClipRequestStatus.SUCCEEDED
    assert row.provider_job_id == "job-1"
    assert row.result_asset_id is not None
    assert row.scene_graph_json["scenes"][0].get("has_clip") is True
    assert row.scene_graph_json["scenes"][0].get("clip_asset_id") == str(row.result_asset_id)

    async def _load_video() -> GeneratedVisualAssetTable:
        from app.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            video = await session.get(
                GeneratedVisualAssetTable, UUID(body1["result_asset_id"])
            )
            assert video is not None
            return video

    video = asyncio.run(_load_video())
    assert video.asset_type == GeneratedVisualAssetType.VIDEO_CLIP
    assert str(video.parent_asset_id) == asset_id
