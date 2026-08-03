"""Phase 7.0 — Telegram publishing adapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.core.config import get_settings
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Telegram publish"},
        headers=headers,
    ).json()["id"]


def _approve_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Telegram asset", "body": "Hello Telegram"},
        headers=headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    return asset_id


def _telegram_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    chat_id: str = "-100123456",
    parse_mode: str | None = None,
    disable_web_page_preview: bool = False,
) -> str:
    config: dict = {"chat_id": chat_id}
    if parse_mode is not None:
        config["parse_mode"] = parse_mode
    if disable_web_page_preview:
        config["disable_web_page_preview"] = True
    response = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "TG", "type": "telegram", "config": config},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _queue_job(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    asset_id: str,
    channel_id: str,
) -> str:
    return client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=headers,
    ).json()["id"]


def test_telegram_channel_config_forbids_bot_token(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={
            "name": "Bad TG",
            "type": "telegram",
            "config": {"chat_id": "1", "bot_token": "secret"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_telegram_adapter_success_records_message_id_and_no_token_leak(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_PUBLICATION_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_PUBLICATION_BOT_TOKEN", "tg_test_token")

    project_id = _project_id(client, auth_headers)
    channel_id = _telegram_channel(client, auth_headers, project_id, parse_mode=None)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(client, auth_headers, project_id, asset_id=asset_id, channel_id=channel_id)

    resp = httpx.Response(
        200,
        content=json.dumps({"ok": True, "result": {"message_id": 123}}).encode("utf-8"),
        request=httpx.Request("POST", "https://api.telegram.org/bot***/sendMessage"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=resp):
        processed = client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        assert processed.status_code == 200

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "succeeded"

    deliveries = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    blob = json.dumps(deliveries)
    assert "telegram_message_id=123" in blob
    assert "tg_test_token" not in blob

    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("status_code", "expected_code", "expected_terminal"),
    [
        (401, "auth_error", True),
        (403, "auth_error", True),
        (400, "bad_request", True),
        (429, "rate_limit", False),
    ],
)
def test_telegram_adapter_error_normalization(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_code: str,
    expected_terminal: bool,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_PUBLICATION_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_PUBLICATION_BOT_TOKEN", "tg_test_token")

    project_id = _project_id(client, auth_headers)
    channel_id = _telegram_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(client, auth_headers, project_id, asset_id=asset_id, channel_id=channel_id)

    resp = httpx.Response(
        status_code,
        content=json.dumps({"ok": False, "description": "bad"}).encode("utf-8"),
        request=httpx.Request("POST", "https://api.telegram.org/bot***/sendMessage"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=resp):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )

    deliveries = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    assert deliveries
    assert deliveries[0]["error_code"] == expected_code

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    if expected_terminal:
        assert job["status"] == "failed"
    else:
        assert job["status"] in ("queued", "running", "failed")

    get_settings.cache_clear()


def test_telegram_adapter_disabled_flag_fails_without_network(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_PUBLICATION_ENABLED", "false")
    monkeypatch.setenv("TELEGRAM_PUBLICATION_BOT_TOKEN", "tg_test_token")

    project_id = _project_id(client, auth_headers)
    channel_id = _telegram_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(client, auth_headers, project_id, asset_id=asset_id, channel_id=channel_id)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        mock_post.assert_not_called()

    deliveries = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    blob = json.dumps(deliveries)
    assert "telegram_publication_disabled" in blob

    get_settings.cache_clear()


def test_replay_failed_telegram_job_works(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_PUBLICATION_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_PUBLICATION_BOT_TOKEN", "tg_test_token")

    project_id = _project_id(client, auth_headers)
    channel_id = _telegram_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = _queue_job(client, auth_headers, project_id, asset_id=asset_id, channel_id=channel_id)

    resp = httpx.Response(
        500,
        content=json.dumps({"ok": False, "description": "server"}).encode("utf-8"),
        request=httpx.Request("POST", "https://api.telegram.org/bot***/sendMessage"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=resp):
        for _ in range(3):
            client.post(
                f"/projects/{project_id}/publication-jobs/process",
                headers=auth_headers,
            )

    replay = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "queued"

    get_settings.cache_clear()


def test_telegram_media_send_photo_success(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_PUBLICATION_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_PUBLICATION_BOT_TOKEN", "tg_test_token")

    project_id = _project_id(client, auth_headers)
    channel_id = _telegram_channel(client, auth_headers, project_id)
    # media_url lives in metadata and flows into version_metadata on approve
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "With photo",
            "body": "Caption",
            "metadata": {"media_url": "https://example.com/photo.jpg"},
        },
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )
    job_id = _queue_job(client, auth_headers, project_id, asset_id=asset_id, channel_id=channel_id)

    resp = httpx.Response(
        200,
        content=json.dumps({"ok": True, "result": {"message_id": 777}}).encode("utf-8"),
        request=httpx.Request("POST", "https://api.telegram.org/bot***/sendPhoto"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=resp):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )

    deliveries = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    blob = json.dumps(deliveries)
    assert "method=sendPhoto" in blob
    assert "media_type=photo" in blob
    assert "telegram_message_id=777" in blob

    get_settings.cache_clear()


def test_telegram_media_caption_too_long_skips(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_PUBLICATION_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_PUBLICATION_BOT_TOKEN", "tg_test_token")

    project_id = _project_id(client, auth_headers)
    channel_id = _telegram_channel(client, auth_headers, project_id)
    long_body = "x" * 2000
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "Too long",
            "body": long_body,
            "metadata": {"media_url": "https://example.com/photo.jpg"},
        },
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )
    job_id = _queue_job(client, auth_headers, project_id, asset_id=asset_id, channel_id=channel_id)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        mock_post.assert_not_called()

    deliveries = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    assert deliveries
    assert deliveries[0]["status"] == "skipped"
    assert deliveries[0]["error_code"] == "caption_too_long"

    get_settings.cache_clear()


def test_telegram_media_url_with_token_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_PUBLICATION_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_PUBLICATION_BOT_TOKEN", "tg_test_token")

    project_id = _project_id(client, auth_headers)
    channel_id = _telegram_channel(client, auth_headers, project_id)
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "Bad media",
            "body": "Caption",
            "metadata": {"media_url": "https://example.com/p.jpg?token=secret123"},
        },
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )
    job_id = _queue_job(client, auth_headers, project_id, asset_id=asset_id, channel_id=channel_id)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        mock_post.assert_not_called()

    deliveries = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    assert deliveries
    assert deliveries[0]["status"] == "skipped"
    assert deliveries[0]["error_code"] in {
        "media_url_rejected_for_secrets",
        "media_url_contains_secret_params",
        "media_url_contains_secret_values",
    }

    get_settings.cache_clear()

