"""VS.2A-R — duration contract, capability truth, result validation."""

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
from app.media_generation.video_clip_download import VideoDownloadResult
from app.media_generation.video_duration_probe import (
    classify_duration_validation,
    probe_mp4_duration_seconds,
)
from app.media_generation.video_router import build_video_router
from app.schemas.contracts import (
    DurationValidationStatus,
    GeneratedVisualAssetStatus,
    GeneratedVisualAssetType,
    GeneratedVisualGenerationMode,
    UserRequestStatus,
    VideoClipRequestStatus,
)
from app.video_studio.provider_duration_capabilities import (
    assert_single_clip_duration_supported,
    provider_payload_duration_seconds,
    provider_reported_duration_seconds,
    provider_supported_single_clip_durations,
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
            created = await auth_service.create_api_key(user.id, "pytest-vs2ar-owner")
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
    monkeypatch.setenv("GPTUNNEL_VIDEO_MODEL", "glabs-veo-3-1-fast")
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
                text="VS.2A-R duration test image",
                normalized_text="VS.2A-R duration test image",
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
                    review_notes="vs2ar_accepted",
                )
            )
            await session.commit()
            return str(asset_id)

    return asyncio.run(_seed())


def test_provider_capability_truth_for_veo() -> None:
    model = "glabs-veo-3-1-fast"
    assert provider_supported_single_clip_durations(model) == (8,)
    assert provider_payload_duration_seconds(model) is None
    assert provider_reported_duration_seconds(model) == 8
    assert_single_clip_duration_supported(8, model)
    with pytest.raises(Exception):
        assert_single_clip_duration_supported(5, model)


def test_classify_duration_validation() -> None:
    assert classify_duration_validation(requested_seconds=8, actual_seconds=8.0)[0] == (
        DurationValidationStatus.MATCHED
    )
    assert classify_duration_validation(requested_seconds=8, actual_seconds=8.3)[0] == (
        DurationValidationStatus.WITHIN_TOLERANCE
    )
    assert classify_duration_validation(requested_seconds=5, actual_seconds=8.2)[0] == (
        DurationValidationStatus.MISMATCH
    )


def test_smoke_mp4_measured_duration_if_present() -> None:
    smoke_mp4 = Path(
        "data/generated_visuals/927583e5-e95c-4cb7-92a8-d480cbdeef24.mp4"
    )
    if not smoke_mp4.is_file():
        pytest.skip("VR.3 smoke MP4 not present locally")
    measured = probe_mp4_duration_seconds(smoke_mp4)
    assert 7.5 <= measured <= 8.5
    status, delta = classify_duration_validation(requested_seconds=5, actual_seconds=measured)
    assert status == DurationValidationStatus.MISMATCH
    assert delta > 2.0


def test_preview_rejects_unsupported_duration(
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
            "duration_seconds": 5,
            "aspect_ratio": "16:9",
        },
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body.get("safe_message") == "provider_duration_not_supported"


def test_capabilities_expose_provider_supported_durations(
    client: TestClient,
    owner_headers: dict[str, str],
    live_video_env: None,
) -> None:
    resp = client.get("/media-generation/video-studio/capabilities", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider_supported_single_clip_durations_seconds"] == [8]


def test_generate_mismatch_not_silently_succeeded(
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

    async def fake_create(_request):
        return (
            "gptunnel_creativelab",
            GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id="job-mismatch",
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
        lambda _path: 10.5,
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
            headers={**owner_headers, "Idempotency-Key": "vs2ar-mismatch-001"},
            json={"approved": True},
        )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body["status"] == "result_requires_review"
    assert body["can_accept"] is False
    assert body["duration_validation_status"] == "mismatch"
    assert body["actual_duration_seconds"] == 10.5
    assert "отличается" in body["user_message_ru"].lower()

    async def _load_row() -> VideoClipRequestTable:
        from app.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            row = await session.get(VideoClipRequestTable, UUID(clip_id))
            assert row is not None
            return row

    row = asyncio.run(_load_row())
    assert row.status == VideoClipRequestStatus.RESULT_REQUIRES_REVIEW
    evidence = row.execution_evidence_json
    assert evidence["duration_validation_status"] == "mismatch"
    assert evidence["measured_mp4_duration"] == 10.5


def test_generate_matched_duration_succeeds(
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

    async def fake_create(_request):
        return (
            "gptunnel_creativelab",
            GatewayCreateResult(
                status=GatewayInvokeStatus.QUEUED,
                job_id="job-match",
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

    async def fake_download(_settings, *, url, mime_hint):
        _ = url, mime_hint
        return VideoDownloadResult(
            temp_path=tmp_path / "fake2.mp4",
            mime="video/mp4",
            checksum_sha256="cafebabe",
            size_bytes=16,
        )

    fake_file = tmp_path / "fake2.mp4"
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
        gen = client.post(
            f"/media-generation/video-clips/{clip_id}/generate",
            headers={**owner_headers, "Idempotency-Key": "vs2ar-match-001"},
            json={"approved": True},
        )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body["status"] == "succeeded"
    assert body["can_accept"] is True
    assert body["duration_validation_status"] == "matched"
