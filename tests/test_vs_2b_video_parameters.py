"""VS.2B — video parameters contract, long-form planning, capabilities API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.video_studio.contracts import (
    REQUESTED_VIDEO_DURATION_SECONDS,
    duration_mode_for,
    validate_requested_duration,
)
from app.video_studio.long_form_planner import plan_long_form_scenes
from app.video_studio.router_capabilities import RouteCapabilities


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
            created = await auth_service.create_api_key(user.id, "pytest-vs2b")
            return {"Authorization": f"Bearer {created.plain_key}"}

    return asyncio.run(_go())


def test_duration_catalog_and_modes() -> None:
    assert len(REQUESTED_VIDEO_DURATION_SECONDS) == 10
    assert duration_mode_for(8).value == "single_clip"
    assert duration_mode_for(90).value == "long_form"
    with pytest.raises(Exception):
        validate_requested_duration(20)


def test_long_form_scene_durations_sum_exactly() -> None:
    caps = RouteCapabilities(
        single_clip_min_seconds=5,
        single_clip_max_seconds=15,
        target_scene_duration_seconds=8,
        provider_supported_single_clip_durations_seconds=(8,),
        native_aspect_ratios=frozenset({"16:9"}),
        post_process_aspect_ratios=frozenset(),
        estimated_cost_units_per_clip="49",
        router_connected=True,
    )
    plan90 = plan_long_form_scenes(90, caps)
    assert sum(plan90.scene_durations_seconds) == 90
    assert plan90.scene_count == len(plan90.scene_durations_seconds)
    assert all(d > 0 for d in plan90.scene_durations_seconds)

    plan300 = plan_long_form_scenes(300, caps)
    assert sum(plan300.scene_durations_seconds) == 300


def test_capabilities_endpoint(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.get("/media-generation/video-studio/capabilities", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requested_durations_seconds"] == list(REQUESTED_VIDEO_DURATION_SECONDS)
    assert body["provider_supported_single_clip_durations_seconds"] == [8]
    assert body["long_form_planning_available"] is True
    assert body["long_form_generation_available"] is False
    assert len(body["aspect_ratios"]) == 5
    assert len(body["camera_movements"]) >= 20
    assert body["camera_movements_catalog_status"] == "BLOCKER"


def test_preview_single_clip_8s(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.post(
        "/media-generation/video-studio/preview",
        headers=owner_headers,
        json={
            "requested_duration_seconds": 8,
            "aspect_ratio": "16:9",
            "source_mode": "no_start_frame",
            "camera_movement_id": "dolly_in",
            "scene_description": "Product hero shot with subtle motion",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["duration_mode"] == "single_clip"
    assert body["scene_count"] == 1
    assert "provider" not in str(body).lower() or "estimated_cost_label" in body


def test_preview_long_form_90s_no_generation(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/media-generation/video-studio/preview",
        headers=owner_headers,
        json={
            "requested_duration_seconds": 90,
            "aspect_ratio": "9:16",
            "source_mode": "no_start_frame",
            "camera_movement_id": "dolly_in",
            "scene_description": "Story arc for social campaign",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["duration_mode"] == "long_form"
    assert body["plan_only"] is True
    assert body["generation_available"] is False
    assert body["primary_action_ru"] == "Подготовить план ролика"
    assert sum(body["scene_durations_seconds"]) == 90


def test_preview_300s_does_not_call_gateway(
    client: TestClient, owner_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    called = {"n": 0}

    async def boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("gateway must not be called for long-form preview")

    monkeypatch.setattr(
        "app.media_generation.video_router.VideoRouter.create",
        boom,
    )
    resp = client.post(
        "/media-generation/video-studio/preview",
        headers=owner_headers,
        json={
            "requested_duration_seconds": 300,
            "aspect_ratio": "21:9",
            "source_mode": "no_start_frame",
            "camera_movement_id": "slow_cinematic_move",
            "scene_description": "Cinematic brand film with wide establishing shots",
        },
    )
    assert resp.status_code == 200, resp.text
    assert called["n"] == 0
    assert sum(resp.json()["scene_durations_seconds"]) == 300


def test_commercial_clip_rejects_long_form_duration(
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    import asyncio
    from uuid import uuid4

    from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
    from app.db.models.user_request import UserRequestTable
    from app.schemas.contracts import (
        GeneratedVisualAssetStatus,
        GeneratedVisualAssetType,
        GeneratedVisualGenerationMode,
        UserRequestStatus,
    )
    from tests.test_vs_2a_commercial_slice import _seed_source_image

    monkeypatch.setenv("VIDEO_GENERATION_ENABLED", "true")
    monkeypatch.setenv("GPTUNNEL_API_KEY", "test-key")
    get_settings.cache_clear()

    asset_id = _seed_source_image(client, owner_headers, tmp_path, monkeypatch)
    resp = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": asset_id,
            "motion_brief": "Test motion",
            "duration_seconds": 90,
            "aspect_ratio": "16:9",
            "camera_movement_id": "dolly_in",
        },
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body.get("error_code") == "long_form_requires_plan_preview"


def test_camera_movement_id_not_label(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.post(
        "/media-generation/video-studio/preview",
        headers=owner_headers,
        json={
            "requested_duration_seconds": 8,
            "aspect_ratio": "16:9",
            "source_mode": "no_start_frame",
            "camera_movement_id": "Медленный наезд",
            "scene_description": "Invalid label used as id should fail",
        },
    )
    assert resp.status_code == 400


def test_all_aspect_ratios_validate(client: TestClient, owner_headers: dict[str, str]) -> None:
    for aspect in ("9:16", "16:9", "1:1", "4:5", "21:9"):
        resp = client.post(
            "/media-generation/video-studio/preview",
            headers=owner_headers,
            json={
                "requested_duration_seconds": 8,
                "aspect_ratio": aspect,
                "source_mode": "no_start_frame",
                "camera_movement_id": "dolly_in",
                "scene_description": f"Aspect ratio validation {aspect}",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["aspect_ratio"] == aspect


def test_rejects_arbitrary_duration(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.post(
        "/media-generation/video-studio/preview",
        headers=owner_headers,
        json={
            "requested_duration_seconds": 20,
            "aspect_ratio": "16:9",
            "source_mode": "no_start_frame",
            "camera_movement_id": "dolly_in",
            "scene_description": "Unsupported duration",
        },
    )
    assert resp.status_code in {400, 409}
    assert resp.json().get("error_code") == "unsupported_video_duration"
