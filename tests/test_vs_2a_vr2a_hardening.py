"""VR.2A hardening tests — outcome_unknown, reconcile, download limits, accepted source."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
from app.db.models.user_request import UserRequestTable
from app.db.models.video_clip_request import VideoClipRequestTable
from app.media_generation.gateway import (
    GatewayCreateResult,
    GatewayInvokeStatus,
    GatewayPollResult,
)
from app.media_generation.video_clip_download import VideoDownloadError, VideoDownloadResult
from app.media_generation.video_router import build_video_router
from app.schemas.contracts import (
    GeneratedVisualAssetStatus,
    GeneratedVisualAssetType,
    GeneratedVisualGenerationMode,
    UserRequestStatus,
    VideoClipRequestStatus,
)


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
            created = await auth_service.create_api_key(user.id, "pytest-vr2a-owner")
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


def _seed_accepted_image(
    client: TestClient,
    headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    user_accepted: bool | None = True,
    asset_type: GeneratedVisualAssetType = GeneratedVisualAssetType.USER_RESULT,
) -> str:
    storage = tmp_path / "visuals"
    storage.mkdir()
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(storage))
    get_settings.cache_clear()

    owner_id = UUID(client.get("/auth/me", headers=headers).json()["id"])

    async def _seed() -> str:
        from app.db.session import get_session_factory

        asset_id = uuid4()
        img = storage / f"{asset_id}.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 64)
        factory = get_session_factory()
        async with factory() as session:
            ur = UserRequestTable(
                owner_id=owner_id,
                text="VR.2A neutral road scene",
                normalized_text="VR.2A neutral road scene",
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
                    asset_type=asset_type,
                    prompt_summary="neutral road landscape for smoke",
                    mime_type="image/png",
                    content_path=str(img),
                    storage_uri=f"/generated-visual-assets/{asset_id}/content",
                    status=GeneratedVisualAssetStatus.SUCCEEDED,
                    user_accepted=user_accepted,
                    review_notes="vr2a_accepted" if user_accepted else None,
                )
            )
            await session.commit()
            return str(asset_id)

    return asyncio.run(_seed())


def test_preview_requires_accepted_source(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_accepted_image(
        client, owner_headers, tmp_path, monkeypatch, user_accepted=None
    )
    resp = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Slow pan over calm road",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "source_asset_not_accepted"


def test_preview_rejects_identity_reference_asset(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_accepted_image(
        client,
        owner_headers,
        tmp_path,
        monkeypatch,
        asset_type=GeneratedVisualAssetType.IDENTITY_AB_CHILD,
    )
    resp = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Slow pan",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "source_asset_identity_reference_blocked"


def test_poll_timeout_marks_outcome_unknown(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_accepted_image(client, owner_headers, tmp_path, monkeypatch)
    preview = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Slow pan over road",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    clip_id = preview.json()["clip_request_id"]

    async def fake_create(_request):
        return (
            "gptunnel_creativelab",
            GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id="job-timeout-1",
                paid_call_performed=True,
            ),
        )

    async def fake_poll(_code, _job):
        return GatewayPollResult(
            status=GatewayInvokeStatus.FAILED,
            detail_code="gptunnel_poll_timeout",
            paid_call_performed=True,
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
        gen = client.post(
            f"/media-generation/video-clips/{clip_id}/generate",
            headers={**owner_headers, "Idempotency-Key": "vr2a-timeout-001"},
            json={"approved": True},
        )
    assert gen.status_code == 200
    body = gen.json()
    assert body["status"] == "outcome_unknown"
    assert body["can_reconcile"] is True
    assert body["can_retry_motion"] is False
    assert "gptunnel" not in body["user_message_ru"].lower()

    async def _load_row() -> VideoClipRequestTable:
        from app.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            row = await session.get(VideoClipRequestTable, UUID(clip_id))
            assert row is not None
            return row

    row = asyncio.run(_load_row())
    assert row.provider_job_id == "job-timeout-1"
    assert row.status == VideoClipRequestStatus.OUTCOME_UNKNOWN


def test_reconcile_completed_creates_asset(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_accepted_image(client, owner_headers, tmp_path, monkeypatch)
    preview = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Slow pan",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    clip_id = preview.json()["clip_request_id"]

    async def fake_create(_request):
        return (
            "gptunnel_creativelab",
            GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id="job-reconcile-1",
                paid_call_performed=True,
            ),
        )

    async def fake_poll_timeout(_code, _job):
        return GatewayPollResult(
            status=GatewayInvokeStatus.FAILED,
            detail_code="gptunnel_poll_timeout",
            paid_call_performed=True,
        )

    async def fake_poll_done(_code, _job):
        return GatewayPollResult(
            status=GatewayInvokeStatus.DONE,
            url="https://example.test/clip.mp4",
            mime="video/mp4",
            paid_call_performed=True,
        )

    async def fake_download(_settings, *, url, mime_hint):
        _ = url, mime_hint
        path = tmp_path / "dl.mp4"
        path.write_bytes(b"mp4-bytes")
        return VideoDownloadResult(
            temp_path=path,
            mime="video/mp4",
            checksum_sha256="abc",
            size_bytes=8,
        )

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
        router.poll = fake_poll_timeout  # type: ignore[method-assign]
        return router

    with patch(
        "app.services.video_clip_commercial_service.build_video_router",
        side_effect=build_mock_router,
    ):
        client.post(
            f"/media-generation/video-clips/{clip_id}/generate",
            headers={**owner_headers, "Idempotency-Key": "vr2a-reconcile-001"},
            json={"approved": True},
        )

    def build_reconcile_router(settings):
        router = build_video_router(settings)
        router.poll = fake_poll_done  # type: ignore[method-assign]
        return router

    with patch(
        "app.services.video_clip_commercial_service.build_video_router",
        side_effect=build_reconcile_router,
    ):
        rec = client.post(
            f"/media-generation/video-clips/{clip_id}/reconcile",
            headers=owner_headers,
        )
    assert rec.status_code == 200, rec.text
    body = rec.json()
    assert body["status"] == "succeeded"
    assert body["result_asset_id"]


def test_reconcile_without_provider_job_id_is_409(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_accepted_image(client, owner_headers, tmp_path, monkeypatch)
    preview = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Slow pan",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    clip_id = preview.json()["clip_request_id"]
    resp = client.post(
        f"/media-generation/video-clips/{clip_id}/reconcile",
        headers=owner_headers,
    )
    assert resp.status_code == 409


def test_download_too_large_marks_outcome_unknown(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_accepted_image(client, owner_headers, tmp_path, monkeypatch)
    preview = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Slow pan",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    clip_id = preview.json()["clip_request_id"]

    async def fake_create(_request):
        return (
            "gptunnel_creativelab",
            GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id="job-large-1",
                paid_call_performed=True,
            ),
        )

    async def fake_poll(_code, _job):
        return GatewayPollResult(
            status=GatewayInvokeStatus.DONE,
            url="https://example.test/large.mp4",
            mime="video/mp4",
            paid_call_performed=True,
        )

    async def fake_download(_settings, *, url, mime_hint):
        _ = url, mime_hint
        raise VideoDownloadError("result_download_too_large", "too large")

    monkeypatch.setattr(
        "app.services.video_clip_commercial_service.download_provider_video_to_temp",
        fake_download,
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
        gen = client.post(
            f"/media-generation/video-clips/{clip_id}/generate",
            headers={**owner_headers, "Idempotency-Key": "vr2a-large-001"},
            json={"approved": True},
        )
    assert gen.status_code == 200
    assert gen.json()["status"] == "outcome_unknown"
    assert gen.json()["can_reconcile"] is True


def test_same_idempotency_key_returns_same_request_without_second_create(
    live_video_env: None,
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset_id = _seed_accepted_image(client, owner_headers, tmp_path, monkeypatch)
    preview = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Slow pan",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    clip_id = preview.json()["clip_request_id"]
    create_calls = 0

    async def fake_create(_request):
        nonlocal create_calls
        create_calls += 1
        return (
            "gptunnel_creativelab",
            GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id="job-idem-1",
                paid_call_performed=True,
            ),
        )

    async def fake_poll(_code, _job):
        return GatewayPollResult(
            status=GatewayInvokeStatus.FAILED,
            detail_code="gptunnel_poll_timeout",
            paid_call_performed=True,
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
        headers = {**owner_headers, "Idempotency-Key": "vr2a-idem-shared"}
        first = client.post(
            f"/media-generation/video-clips/{clip_id}/generate",
            headers=headers,
            json={"approved": True},
        )
        second = client.post(
            f"/media-generation/video-clips/{clip_id}/generate",
            headers=headers,
            json={"approved": True},
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["clip_request_id"] == second.json()["clip_request_id"]
    assert create_calls == 1
