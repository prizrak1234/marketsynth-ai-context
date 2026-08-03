"""Phase 6.2 — real webhook publishing adapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES, get_agent_tool_matrix
from app.core.config import get_settings
from app.events.webhook_delivery import sign_webhook_body, truncate_response_preview
from app.publishing.adapters.webhook import (
    build_publication_payload,
    build_publication_request_headers,
    dispatch_webhook_publication,
)
from app.publishing.webhook_channel_config import validate_webhook_channel_config
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Webhook publish"},
        headers=headers,
    ).json()["id"]


def _approve_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Hook asset", "body": "Body text"},
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


def _webhook_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    url: str,
    signing_secret: str | None = "whsec_test",
    extra_headers: dict[str, str] | None = None,
) -> str:
    config: dict = {"url": url}
    if signing_secret is not None:
        config["signing_secret"] = signing_secret
    if extra_headers:
        config["headers"] = extra_headers
    response = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Webhook out", "type": "webhook", "config": config},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_webhook_channel_requires_valid_url(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    missing = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Bad", "type": "webhook", "config": {}},
        headers=auth_headers,
    )
    assert missing.status_code == 409

    bad_scheme = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={
            "name": "Bad",
            "type": "webhook",
            "config": {"url": "ftp://example.com/hook"},
        },
        headers=auth_headers,
    )
    assert bad_scheme.status_code == 409


def test_config_preview_hides_signing_secret(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={
            "name": "Secret hook",
            "type": "webhook",
            "config": {
                "url": "https://example.com/publish?token=abc",
                "signing_secret": "super-secret",
                "headers": {"Authorization": "Bearer xyz"},
            },
        },
        headers=auth_headers,
    ).json()
    preview = channel["config_preview"]
    assert preview.get("signing_secret") == "***"
    assert "super-secret" not in str(preview)
    assert "?" not in preview.get("url", "")
    assert preview["headers"]["Authorization"] == "***"


def test_successful_webhook_marks_job_succeeded(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(
        client,
        auth_headers,
        project_id,
        url="https://example.com/publish?sig=hidden",
    )
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    mock_response = httpx.Response(
        200,
        text='{"ok":true}',
        request=httpx.Request("POST", "https://example.com/publish"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        batch = client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
    assert batch.json()["succeeded_count"] == 1

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "succeeded"


def test_non_2xx_failed_log_and_retry(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(
        client,
        auth_headers,
        project_id,
        url="https://example.com/publish",
        signing_secret=None,
    )
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    mock_response = httpx.Response(
        502,
        text="bad gateway",
        request=httpx.Request("POST", "https://example.com/publish"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        first = client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        ).json()
    assert first["requeued_count"] == 1

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "queued"
    assert job["attempts"] == 1

    logs = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    assert logs[0]["status"] == "failed"
    assert logs[0]["error_code"] == "http_502"


def test_timeout_safe_logged(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(
        client,
        auth_headers,
        project_id,
        url="https://example.com/publish",
        signing_secret=None,
    )
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.TimeoutException("timed out"),
    ):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )

    logs = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    assert logs[0]["error_code"] == "timeout"
    assert "traceback" not in (logs[0]["error_message"] or "").lower()


@pytest.mark.asyncio
async def test_max_attempts_job_failed(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PUBLICATION_JOB_MAX_ATTEMPTS", "3")
    get_settings.cache_clear()

    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(
        client,
        auth_headers,
        project_id,
        url="https://example.com/publish",
        signing_secret=None,
    )
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    mock_response = httpx.Response(
        500,
        request=httpx.Request("POST", "https://example.com/publish"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        for _ in range(3):
            client.post(
                f"/projects/{project_id}/publication-jobs/process",
                headers=auth_headers,
            )

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "failed"
    assert job["attempts"] == 3
    get_settings.cache_clear()


def test_signature_header_valid() -> None:
    from uuid import uuid4

    from app.db.models.marketing import ContentAssetVersionTable
    from app.db.models.publishing import PublicationJobTable, PublishingChannelTable
    from app.marketing.contracts import ContentAssetType

    job = PublicationJobTable(
        owner_id=uuid4(),
        project_id=uuid4(),
        asset_id=uuid4(),
        asset_version_number=1,
        channel_id=uuid4(),
        payload_preview={"asset_type": ContentAssetType.EMAIL.value},
    )
    channel = PublishingChannelTable(
        owner_id=job.owner_id,
        project_id=job.project_id,
        name="Hook",
        channel_type="webhook",
        channel_config={
            "url": "https://example.com/publish",
            "signing_secret": "whsec_unit",
        },
    )
    version = ContentAssetVersionTable(
        owner_id=job.owner_id,
        project_id=job.project_id,
        asset_id=job.asset_id,
        version_number=1,
        title="T",
        body="B",
    )
    payload = build_publication_payload(job, channel, version)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    timestamp = "2026-05-29T12:00:00+00:00"
    headers = build_publication_request_headers(
        job=job,
        timestamp=timestamp,
        body=body,
        signing_secret="whsec_unit",
        extra_headers=None,
    )
    expected = sign_webhook_body(signing_secret="whsec_unit", timestamp=timestamp, body=body)
    assert headers["X-BotFazer-Signature"] == expected
    assert headers["X-BotFazer-Publication-Job-Id"] == str(job.id)


def test_async_client_uses_trust_env_false() -> None:
    from uuid import uuid4

    from app.db.models.marketing import ContentAssetVersionTable
    from app.db.models.publishing import PublicationJobTable, PublishingChannelTable

    job = PublicationJobTable(
        owner_id=uuid4(),
        project_id=uuid4(),
        asset_id=uuid4(),
        asset_version_number=1,
        channel_id=uuid4(),
        payload_preview={"asset_type": "email"},
    )
    channel = PublishingChannelTable(
        owner_id=job.owner_id,
        project_id=job.project_id,
        name="Hook",
        channel_type="webhook",
        channel_config={"url": "https://example.com/publish"},
    )
    version = ContentAssetVersionTable(
        owner_id=job.owner_id,
        project_id=job.project_id,
        asset_id=job.asset_id,
        version_number=1,
        title="T",
        body="B",
    )
    captured: dict = {}

    class _RecordingClient:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

        async def post(self, *_args, **_kwargs):
            return httpx.Response(200, request=httpx.Request("POST", "https://example.com"))

        async def aclose(self) -> None:
            return None

    with patch("app.publishing.adapters.webhook.httpx.AsyncClient", _RecordingClient):
        import asyncio

        asyncio.run(
            dispatch_webhook_publication(
                job,
                channel,
                version,
                timeout_seconds=5,
            ),
        )
    assert captured.get("trust_env") is False


def test_delivery_log_hides_url_query(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _webhook_channel(
        client,
        auth_headers,
        project_id,
        url="https://example.com/publish?token=secret123",
        signing_secret=None,
    )
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    mock_response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://example.com/publish"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )

    logs = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    log_blob = json.dumps(logs)
    assert "secret123" not in log_blob
    assert "token=" not in log_blob
    assert "https://example.com/publish" in (logs[0]["response_preview"] or "")


def test_response_preview_truncated() -> None:
    long_text = "y" * 600
    preview = truncate_response_preview(long_text)
    assert len(preview) == 500


def test_custom_adapter_still_noop(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Custom", "type": "custom", "config": {}},
        headers=auth_headers,
    ).json()["id"]
    asset_id = _approve_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        batch = client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        mock_post.assert_not_called()
    assert batch.json()["succeeded_count"] == 1


def test_telegram_disabled_by_default(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "TG", "type": "telegram", "config": {"chat_id": "1"}},
        headers=auth_headers,
    ).json()["id"]
    asset_id = _approve_asset(client, auth_headers, project_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        mock_post.assert_not_called()

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "failed"
    logs = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    assert logs[0]["status"] == "skipped"
    assert logs[0]["error_code"] == "telegram_publication_disabled"


def test_agent_tool_matrix_unchanged() -> None:
    matrix = get_agent_tool_matrix()
    assert "orchestrator" in matrix
    names = {tool.name for tool in get_tool_registry().list_registered()}
    assert not any("publish" in n or "publication" in n for n in names)
    for forbidden in FORBIDDEN_AGENT_TOOL_NAMES:
        assert forbidden not in names


def test_validate_webhook_config_normalizes() -> None:
    cfg = validate_webhook_channel_config(
        {
            "url": "https://hooks.example.com/publish",
            "signing_secret": "sec",
            "headers": {"X-Custom": "ok"},
        },
    )
    assert cfg.url.startswith("https://")
    assert cfg.signing_secret == "sec"
