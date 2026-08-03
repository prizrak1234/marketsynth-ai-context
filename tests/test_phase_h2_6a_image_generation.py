"""Phase H2.6A cutover — honest mock vs real openai_images generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.user_request_routing import route_user_request
from app.media_generation.contracts import ImageGenerationResult
from app.schemas.contracts import UserRequestRouteCategory
from app.services.design_image_generation_service import (
    MSG_MOCK,
    MSG_NOT_CONFIGURED,
    MSG_REAL_SUCCESS,
    DesignImageGenerationService,
)


def test_image_route_unchanged() -> None:
    decision = route_user_request(
        "Сгенерируй фотореалистичное изображение девушки за праздничным столом."
    )
    assert decision.category == UserRequestRouteCategory.IMAGE_GENERATION


def test_mock_readiness_is_not_user_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "true")
    monkeypatch.setenv("IMAGE_GENERATION_PROVIDER", "mock")
    monkeypatch.setenv("ALLOW_MOCK_IMAGE_RESULTS", "true")
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    ready = DesignImageGenerationService(session=None, settings=get_settings()).readiness()  # type: ignore[arg-type]
    assert ready["mock_only"] is True
    assert ready["can_generate_user_result"] is False
    assert ready["can_generate_diagnostic"] is True
    assert "api_key" not in ready


def test_mock_provider_honest_ui_copy(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "true")
    monkeypatch.setenv("IMAGE_GENERATION_PROVIDER", "mock")
    monkeypatch.setenv("ALLOW_MOCK_IMAGE_RESULTS", "true")
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "visuals"))
    from app.core.config import get_settings

    get_settings.cache_clear()

    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Сгенерируй фотореалистичное изображение девушки за столом."},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["route_category"] == "image_generation"
    assert body["generation_status"] == "diagnostic"
    assert body["generated_visual_asset_ids"]
    assert MSG_MOCK in body["assistant_message"]
    assert "по вашему описанию" not in body["assistant_message"].lower()
    assert "создано изображение по" not in body["assistant_message"].lower()

    asset_id = body["generated_visual_asset_ids"][0]
    asset = client.get(f"/generated-visual-assets/{asset_id}", headers=auth_headers).json()
    assert asset["generation_mode"] == "mock"
    assert asset["asset_type"] == "diagnostic_placeholder"
    assert asset["provider"] == "mock"
    assert asset["status"] == "diagnostic"
    assert asset["generation_metadata"].get("is_user_result") is False

    ready = client.get("/generated-visual-assets/readiness", headers=auth_headers).json()
    assert ready["can_generate_user_result"] is False
    assert ready["mock_only"] is True


def test_openai_missing_key_honest_error(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "true")
    monkeypatch.setenv("IMAGE_GENERATION_PROVIDER", "openai_images")
    monkeypatch.setenv("ALLOW_MOCK_IMAGE_RESULTS", "false")
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(tmp_path / "visuals"))
    monkeypatch.setenv("IMAGE_GENERATION_FALLBACK_PROVIDER", "")
    monkeypatch.delenv("GPTUNNEL_API_KEY", raising=False)
    monkeypatch.delenv("GPTunnel_API_REY", raising=False)
    monkeypatch.setenv("GPTUNNEL_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    # Force empty keys on settings object used by app
    object.__setattr__(settings, "openai_api_key", None)
    object.__setattr__(settings, "gptunnel_api_key", None)
    object.__setattr__(settings, "image_generation_fallback_provider", "")

    ready = DesignImageGenerationService(session=None, settings=settings).readiness()  # type: ignore[arg-type]
    assert ready["provider_ready"] is False
    assert ready["can_generate_user_result"] is False
    assert ready["real_generation_available"] is False

    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Сгенерируй изображение зимнего вечера."},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["generation_status"] == "unavailable"
    assert body["generated_visual_asset_ids"] == []
    assert MSG_NOT_CONFIGURED in body["assistant_message"] or "не настроен" in body[
        "assistant_message"
    ].lower()


def test_real_provider_success_persists_user_result(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    storage = tmp_path / "visuals"
    storage.mkdir()
    # Tiny valid PNG
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    png_path = storage / "fixture.png"
    # Need larger than MIN_BYTES=512 — pad
    padded = png + (b"\x00" * 600)
    png_path.write_bytes(padded)

    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "true")
    monkeypatch.setenv("IMAGE_GENERATION_PROVIDER", "openai_images")
    monkeypatch.setenv("ALLOW_MOCK_IMAGE_RESULTS", "false")
    monkeypatch.setenv("IMAGE_GENERATION_STORAGE_DIR", str(storage))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    from app.core.config import get_settings

    get_settings.cache_clear()

    async def fake_generate(input_data):  # noqa: ANN001
        return ImageGenerationResult(
            provider="openai_images",
            safe_metadata={"provider": "openai_images", "model": "dall-e-3"},
            provider_asset_ref="https://example.test/image.png",
            mime_type="image/png",
            width=1024,
            height=1024,
        )

    class _FakeProvider:
        async def generate_image(self, input_data):  # noqa: ANN001
            return await fake_generate(input_data)

    async def fake_download(url: str, path: Path) -> bytes:
        from PIL import Image

        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (64, 64), (20, 40, 60)).save(path, format="PNG")
        return path.read_bytes()

    monkeypatch.setattr(
        "app.services.design_image_generation_service.DesignImageGenerationService._resolve_openai_provider",
        lambda self: _FakeProvider(),
    )
    monkeypatch.setattr(
        "app.services.design_image_generation_service._download_to_file",
        fake_download,
    )

    created = client.post(
        "/user-requests",
        headers=auth_headers,
        json={
            "text": (
                "Сгенерируй фотореалистичное изображение девушки "
                "за праздничным столом в новогоднюю ночь."
            ),
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["generation_status"] == "succeeded", body.get("assistant_message")
    assert MSG_REAL_SUCCESS in body["assistant_message"]
    assert "тестовый" not in body["assistant_message"].lower()
    asset_id = body["generated_visual_asset_ids"][0]

    asset = client.get(f"/generated-visual-assets/{asset_id}", headers=auth_headers).json()
    assert asset["generation_mode"] == "real"
    assert asset["asset_type"] == "user_result"
    assert asset["provider"] == "openai_images"
    assert asset["status"] == "succeeded"
    assert asset["checksum"]
    assert asset["width"] == 64
    assert asset["height"] == 64

    refreshed = client.get(f"/user-requests/{body['id']}", headers=auth_headers)
    assert refreshed.status_code == 200
    assert asset_id in refreshed.json()["generated_visual_asset_ids"]

    content = client.get(
        f"/generated-visual-assets/{asset_id}/content",
        headers=auth_headers,
    )
    assert content.status_code == 200
    assert content.content[:8] == b"\x89PNG\r\n\x1a\n"

    other = client.get(
        f"/generated-visual-assets/{asset_id}",
        headers=other_auth_headers,
    )
    assert other.status_code == 404

    ready = client.get("/generated-visual-assets/readiness", headers=auth_headers).json()
    assert ready["can_generate_user_result"] is True
    assert ready["real_generation_available"] is True
    assert "secret" not in str(ready).lower()
    assert "sk-" not in str(ready).lower()


def test_production_forbids_mock_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "true")
    monkeypatch.setenv("IMAGE_GENERATION_PROVIDER", "mock")
    monkeypatch.setenv("ALLOW_MOCK_IMAGE_RESULTS", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()
    ready = DesignImageGenerationService(session=None, settings=get_settings()).readiness()  # type: ignore[arg-type]
    assert ready["allow_mock_image_results"] is False
    assert ready["can_generate_diagnostic"] is False
