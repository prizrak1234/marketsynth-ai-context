"""Phase AI.57 — OpenAI Images provider gated behind feature flags."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.media_generation.contracts import ImageGenerationInput, MediaGenerationProvider
from app.media_generation.provider_registry import assert_provider_selectable, get_image_provider
from app.media_generation.safe_metadata import sanitize_generation_metadata
from fastapi.testclient import TestClient

from tests.media_workflow import approved_content_asset_id, approve_media_brief


def _approved_brief(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = approved_content_asset_id(client, headers, project_id)
    brief_id = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-media-brief",
        json={},
        headers=headers,
    ).json()["media_brief_id"]
    approve_media_brief(client, headers, project_id, brief_id)
    return brief_id


def test_flags_off_blocks_openai_provider() -> None:
    settings = get_settings()
    with pytest.raises(InvalidStateError, match="disabled"):
        assert_provider_selectable(MediaGenerationProvider.OPENAI_IMAGES, settings)


def test_sanitize_strips_forbidden_payload() -> None:
    cleaned = sanitize_generation_metadata(
        {
            "provider": "openai_images",
            "model": "dall-e-3",
            "b64_json": "huge-secret-payload",
            "api_key": "sk-test",
            "data": [{"url": "x"}],
            "image_count": 1,
            "size": "1024x1024",
        },
    )
    assert "b64_json" not in cleaned
    assert "api_key" not in cleaned
    assert "data" not in cleaned
    assert cleaned["provider"] == "openai_images"
    assert cleaned["image_count"] == 1


def test_openai_job_create_rejected_via_api(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post("/projects", json={"name": "AI.57"}, headers=auth_headers).json()["id"]
    brief_id = _approved_brief(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "openai_images"},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_openai_execute_when_enabled_uses_safe_metadata_only(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEDIA_GENERATION_ENABLED", "true")
    monkeypatch.setenv("OPENAI_IMAGES_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    get_settings.cache_clear()

    project_id = client.post("/projects", json={"name": "AI.57 exec"}, headers=auth_headers).json()[
        "id"
    ]
    brief_id = _approved_brief(client, auth_headers, project_id)

    created = client.post(
        f"/projects/{project_id}/media-briefs/{brief_id}/generation-jobs",
        json={"provider": "openai_images"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    job_id = created.json()["id"]

    mock_result = MagicMock()
    mock_result.provider = "openai_images"
    mock_result.safe_metadata = {
        "provider": "openai_images",
        "model": "dall-e-3",
        "image_count": 1,
        "size": "1024x1024",
        "mime_type": "image/png",
    }
    mock_result.provider_asset_ref = "https://example.com/image.png"
    mock_result.storage_uri = None
    mock_result.mime_type = "image/png"
    mock_result.width = 1024
    mock_result.height = 1024

    with patch(
        "app.media_generation.openai_images_provider.OpenAIImagesProvider.generate_image",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        executed = client.post(
            f"/projects/{project_id}/media-generation-jobs/{job_id}/execute",
            headers=auth_headers,
        )
    assert executed.status_code == 200
    meta = executed.json()["result_metadata"]
    assert meta.get("provider") == "openai_images"
    assert "b64" not in str(meta).lower()
    assert "sk-" not in str(meta)


def test_openai_provider_requires_api_key_when_flags_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEDIA_GENERATION_ENABLED", "true")
    monkeypatch.setenv("OPENAI_IMAGES_ENABLED", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(InvalidStateError, match="API key"):
        get_image_provider(MediaGenerationProvider.OPENAI_IMAGES, settings)

    get_settings.cache_clear()


def test_openai_provider_lazy_import_only_when_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEDIA_GENERATION_ENABLED", "true")
    monkeypatch.setenv("OPENAI_IMAGES_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    provider = get_image_provider(MediaGenerationProvider.OPENAI_IMAGES, get_settings())
    assert provider.__class__.__name__ == "OpenAIImagesProvider"
    get_settings.cache_clear()
