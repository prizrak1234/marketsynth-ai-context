"""VS.2A-P-R — persistence, clip restore, owner preview (no paid create)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.models.generated_visual_asset import GeneratedVisualAssetTable
from app.db.models.user_request import UserRequestTable
from app.db.models.video_clip_request import VideoClipRequestTable
from app.media_generation.video_owner_acceptance_preview import (
    CANONICAL_CLIP_REQUEST_ID,
    CANONICAL_RESULT_ASSET_ID,
    CANONICAL_SOURCE_IMAGE_ASSET_ID,
)
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
            created = await auth_service.create_api_key(user.id, "pytest-vs2a-pr-owner")
            return {"Authorization": f"Bearer {created.plain_key}"}

    return asyncio.run(_go())


@pytest.fixture
def other_user_headers(database_url: str) -> dict[str, str]:
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
                    display_name="User",
                    role=UserRole.MEMBER,
                ),
            )
            created = await auth_service.create_api_key(user.id, "pytest-vs2a-pr-user")
            return {"Authorization": f"Bearer {created.plain_key}"}

    return asyncio.run(_go())


def _seed_accepted_image(
    owner_id: UUID,
    tmp_path: Path,
    *,
    user_accepted: bool = True,
    created_order: int = 0,
) -> str:
    storage = tmp_path / "visuals"
    storage.mkdir(exist_ok=True)

    async def _go() -> str:
        from app.db.base import utc_now
        from app.db.session import get_session_factory

        asset_id = uuid4()
        img = storage / f"{asset_id}.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([created_order]) + b"x" * 64)
        factory = get_session_factory()
        async with factory() as session:
            ur = UserRequestTable(
                owner_id=owner_id,
                text=f"VS.2A-P-R image {created_order}",
                normalized_text=f"VS.2A-P-R image {created_order}",
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
                    user_accepted=user_accepted,
                    review_notes="owner_accepted" if user_accepted else "owner_rejected",
                    created_at=utc_now(),
                )
            )
            await session.commit()
            return str(asset_id)

    return asyncio.run(_go())


def _seed_succeeded_clip(
    owner_id: UUID,
    source_asset_id: UUID,
    tmp_path: Path,
) -> tuple[str, str]:
    storage = tmp_path / "visuals"
    storage.mkdir(exist_ok=True)

    async def _go() -> tuple[str, str]:
        from app.db.base import utc_now
        from app.db.session import get_session_factory

        clip_id = uuid4()
        result_id = uuid4()
        mp4 = storage / f"{result_id}.mp4"
        mp4.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"x" * 64)
        factory = get_session_factory()
        async with factory() as session:
            source = await session.get(GeneratedVisualAssetTable, source_asset_id)
            assert source is not None
            session.add(
                VideoClipRequestTable(
                    id=clip_id,
                    owner_id=owner_id,
                    source_image_asset_id=source_asset_id,
                    motion_brief="slow dolly in",
                    duration_seconds=8,
                    aspect_ratio="16:9",
                    request_hash="pytest-hash",
                    status=VideoClipRequestStatus.SUCCEEDED,
                    result_asset_id=result_id,
                    execution_evidence_json={
                        "requested_duration_seconds": 8,
                        "measured_mp4_duration": 8.0,
                        "duration_delta_seconds": 0.0,
                        "duration_validation_status": "matched",
                    },
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
            session.add(
                GeneratedVisualAssetTable(
                    id=result_id,
                    owner_id=owner_id,
                    user_request_id=source.user_request_id,
                    skill_code="design.image_generation",
                    skill_version="1.0",
                    provider="gptunnel_creativelab",
                    generation_mode=GeneratedVisualGenerationMode.REAL,
                    asset_type=GeneratedVisualAssetType.VIDEO_CLIP,
                    prompt_summary="clip",
                    mime_type="video/mp4",
                    content_path=str(mp4),
                    storage_uri=f"/generated-visual-assets/{result_id}/content",
                    status=GeneratedVisualAssetStatus.SUCCEEDED,
                    parent_asset_id=source_asset_id,
                    created_at=utc_now(),
                )
            )
            await session.commit()
            return str(clip_id), str(result_id)

    return asyncio.run(_go())


def test_list_assets_includes_user_accepted(
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "visuals"))
    get_settings.cache_clear()
    me = client.get("/auth/me", headers=owner_headers)
    owner_id = UUID(me.json()["id"])
    asset_id = _seed_accepted_image(owner_id, tmp_path, user_accepted=True)

    resp = client.get("/generated-visual-assets", headers=owner_headers)
    assert resp.status_code == 200
    row = next(a for a in resp.json() if a["id"] == asset_id)
    assert row["user_accepted"] is True


def test_get_clip_by_source_restores_succeeded(
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "visuals"))
    get_settings.cache_clear()
    me = client.get("/auth/me", headers=owner_headers)
    owner_id = UUID(me.json()["id"])
    source_id = _seed_accepted_image(owner_id, tmp_path)
    clip_id, result_id = _seed_succeeded_clip(owner_id, UUID(source_id), tmp_path)

    resp = client.get(
        f"/media-generation/video-clips?source_image_asset_id={source_id}",
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clip_request_id"] == clip_id
    assert body["status"] == "succeeded"
    assert body["execution"]["result_asset_id"] == result_id
    assert body["execution"]["can_reconcile"] is False


def test_get_clip_by_source_tenant_isolation(
    client: TestClient,
    owner_headers: dict[str, str],
    other_user_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "visuals"))
    get_settings.cache_clear()
    me = client.get("/auth/me", headers=owner_headers)
    owner_id = UUID(me.json()["id"])
    source_id = _seed_accepted_image(owner_id, tmp_path)
    _seed_succeeded_clip(owner_id, UUID(source_id), tmp_path)

    resp = client.get(
        f"/media-generation/video-clips?source_image_asset_id={source_id}",
        headers=other_user_headers,
    )
    assert resp.status_code == 200
    assert resp.json() is None


def test_owner_acceptance_preview_guard(
    client: TestClient,
    other_user_headers: dict[str, str],
) -> None:
    resp = client.get(
        "/media-generation/video-clips/owner-acceptance-preview",
        headers=other_user_headers,
    )
    assert resp.status_code == 403


def test_owner_acceptance_preview_binding_when_present(
    client: TestClient,
    owner_headers: dict[str, str],
) -> None:
    resp = client.get(
        "/media-generation/video-clips/owner-acceptance-preview",
        headers=owner_headers,
    )
    if resp.status_code == 404:
        pytest.skip("canonical smoke clip not present in this database")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clip_request_id"] == str(CANONICAL_CLIP_REQUEST_ID)
    assert body["source_image_asset_id"] == str(CANONICAL_SOURCE_IMAGE_ASSET_ID)
    assert body["execution"]["status"] == "succeeded"
    assert body["source_user_accepted"] is True


def test_canonical_asset_content_owner_preview_access(
    client: TestClient,
    owner_headers: dict[str, str],
) -> None:
    probe = client.get(
        "/media-generation/video-clips/owner-acceptance-preview",
        headers=owner_headers,
    )
    if probe.status_code == 404:
        pytest.skip("canonical smoke clip not present in this database")
    content = client.get(
        f"/generated-visual-assets/{CANONICAL_RESULT_ASSET_ID}/content",
        headers=owner_headers,
    )
    assert content.status_code == 200
    assert "video" in (content.headers.get("content-type") or "")


def test_video_review_persists(
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "visuals"))
    get_settings.cache_clear()
    me = client.get("/auth/me", headers=owner_headers)
    owner_id = UUID(me.json()["id"])
    source_id = _seed_accepted_image(owner_id, tmp_path)
    _, result_id = _seed_succeeded_clip(owner_id, UUID(source_id), tmp_path)

    review = client.post(
        f"/generated-visual-assets/{result_id}/review",
        headers=owner_headers,
        json={
            "user_accepted": True,
            "identity_similarity": "not_applicable",
            "brand_similarity": "not_applicable",
            "review_notes": "video_clip_accepted",
        },
    )
    assert review.status_code == 200
    assert review.json()["user_accepted"] is True

    again = client.get(f"/generated-visual-assets/{result_id}", headers=owner_headers)
    assert again.json()["user_accepted"] is True


def test_rejected_image_not_used_for_new_preview(
    client: TestClient,
    owner_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "visuals"))
    get_settings.cache_clear()
    me = client.get("/auth/me", headers=owner_headers)
    owner_id = UUID(me.json()["id"])
    rejected_id = _seed_accepted_image(owner_id, tmp_path, user_accepted=False)

    resp = client.post(
        "/media-generation/video-clips/preview",
        headers=owner_headers,
        json={
            "source_image_asset_id": rejected_id,
            "motion_brief": "Slow camera push-in over product dashboard",
            "duration_seconds": 8,
            "aspect_ratio": "16:9",
        },
    )
    assert resp.status_code == 409
    body = resp.json()
    detail = body.get("detail") or body.get("error_code")
    if isinstance(detail, dict):
        detail = detail.get("error_code") or detail.get("detail")
    assert detail == "source_asset_not_accepted"
