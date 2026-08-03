"""Phase 6.4 — publishing layer safety invariants (freeze guard)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES, get_agent_tool_matrix
from app.core.config import get_settings
from app.db.repositories.content_assets import ContentAssetRepository
from app.events.webhook_delivery import sign_webhook_body
from app.publishing.adapters.webhook import (
    build_publication_payload,
    build_publication_request_headers,
    dispatch_webhook_publication,
)
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Frozen at Phase 6.4 — intentional change requires updating this hash in a dedicated PR.
FROZEN_TOOL_MATRIX_SHA256 = (
    "2f465ba06a6567afd0ce1d9c9f58db2763f7f4a73439628a3f0b1850600a9f9a"
)

FROZEN_FORBIDDEN_AGENT_TOOL_NAMES = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.update",
        "content_asset.archive",
        "memory.write",
        "task.create",
        "agent.update",
    },
)

_PUBLICATION_TOOL_NAME_FRAGMENTS = ("publication", "publishing", "publish_channel")


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Phase 6.4 invariants"},
        headers=headers,
    ).json()["id"]


def _channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    channel_type: str = "custom",
    config: dict | None = None,
    status: str = "active",
) -> str:
    body = {
        "name": "Invariant channel",
        "type": channel_type,
        "config": config or {},
    }
    channel_id = client.post(
        f"/projects/{project_id}/publishing-channels",
        json=body,
        headers=headers,
    ).json()["id"]
    if status != "active":
        client.patch(
            f"/projects/{project_id}/publishing-channels/{channel_id}",
            json={"status": status},
            headers=headers,
        )
    return channel_id


def _draft_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    return client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Invariant", "body": "body"},
        headers=headers,
    ).json()["id"]


def _approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
) -> dict:
    response =     client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


# 1
def test_invariant_draft_asset_cannot_create_publication_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(client, auth_headers, project_id)
    asset_id = _draft_asset(client, auth_headers, project_id)
    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert response.status_code == 409


# 2
def test_invariant_approved_asset_creates_job_with_approved_version(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(client, auth_headers, project_id)
    asset_id = _draft_asset(client, auth_headers, project_id)
    approved = _approve_asset(client, auth_headers, project_id, asset_id)
    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert response.status_code == 201
    job = response.json()
    assert job["asset_version_number"] == approved["approved_version_number"]
    assert approved["approved_version_number"] is not None


# 3
@pytest.mark.asyncio
async def test_invariant_job_pins_approved_version_not_current(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(client, auth_headers, project_id)
    asset_id = _draft_asset(client, auth_headers, project_id)
    approved = _approve_asset(client, auth_headers, project_id, asset_id)
    pinned = approved["approved_version_number"]

    repo = ContentAssetRepository(db_session)
    row = await repo.get_by_id_for_owner(
        UUID(asset_id),
        UUID(approved["owner_id"]),
        UUID(project_id),
    )
    assert row is not None
    row.current_version_number = pinned + 1
    await repo.update(row)
    await db_session.commit()

    job = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    assert job.status_code == 201
    assert job.json()["asset_version_number"] == pinned


# 4
def test_invariant_paused_archived_channel_cannot_create_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(client, auth_headers, project_id)
    asset_id = _draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)

    client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "paused"},
        headers=auth_headers,
    )
    assert (
        client.post(
            f"/projects/{project_id}/publication-jobs",
            json={"asset_id": asset_id, "channel_id": channel_id},
            headers=auth_headers,
        ).status_code
        == 409
    )

    client.patch(
        f"/projects/{project_id}/publishing-channels/{channel_id}",
        json={"status": "archived"},
        headers=auth_headers,
    )
    assert (
        client.post(
            f"/projects/{project_id}/publication-jobs",
            json={"asset_id": asset_id, "channel_id": channel_id},
            headers=auth_headers,
        ).status_code
        == 409
    )


# 5
def test_invariant_channel_config_secrets_not_in_api_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={
            "name": "Secret channel",
            "type": "webhook",
            "config": {
                "url": "https://example.com/hook?token=abc",
                "signing_secret": "whsec_live",
                "headers": {"Authorization": "Bearer secret"},
            },
        },
        headers=auth_headers,
    ).json()
    assert "channel_config" not in channel
    preview = channel["config_preview"]
    assert preview.get("signing_secret") == "***"
    assert "whsec_live" not in json.dumps(channel)
    assert "Bearer secret" not in json.dumps(preview)


# 6
def test_invariant_delivery_logs_hide_url_query(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(
        client,
        auth_headers,
        project_id,
        channel_type="webhook",
        config={"url": "https://example.com/publish?token=secret123"},
    )
    asset_id = _draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    mock_ok = httpx.Response(200, request=httpx.Request("POST", "https://example.com"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_ok):
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
    assert "secret123" not in blob
    assert "token=" not in blob


# 7
def test_invariant_webhook_payload_signs_raw_body() -> None:
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
        channel_config={"url": "https://example.com/publish", "signing_secret": "whsec"},
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
        signing_secret="whsec",
        extra_headers=None,
    )
    expected = sign_webhook_body(signing_secret="whsec", timestamp=timestamp, body=body)
    assert headers["X-BotFazer-Signature"] == expected


# 8
def test_invariant_webhook_uses_trust_env_false() -> None:
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
            dispatch_webhook_publication(job, channel, version, timeout_seconds=5),
        )
    assert captured.get("trust_env") is False


# 9
def test_invariant_succeeded_job_cannot_replay(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(
        client,
        auth_headers,
        project_id,
        channel_type="webhook",
        config={"url": "https://example.com/publish"},
    )
    asset_id = _draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    mock_ok = httpx.Response(200, request=httpx.Request("POST", "https://example.com"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_ok):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
    assert (
        client.post(
            f"/projects/{project_id}/publication-jobs/{job_id}/replay",
            headers=auth_headers,
        ).status_code
        == 409
    )


# 10
def test_invariant_failed_cancelled_job_can_replay(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(
        client,
        auth_headers,
        project_id,
        channel_type="webhook",
        config={"url": "https://example.com/publish"},
    )
    asset_id = _draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]

    mock_fail = httpx.Response(500, request=httpx.Request("POST", "https://example.com"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_fail):
        for _ in range(3):
            client.post(
                f"/projects/{project_id}/publication-jobs/process",
                headers=auth_headers,
            )
    failed_replay = client.post(
        f"/projects/{project_id}/publication-jobs/{job_id}/replay",
        headers=auth_headers,
    )
    assert failed_replay.status_code == 200
    assert failed_replay.json()["status"] == "queued"

    job2_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/publication-jobs/{job2_id}/cancel",
        headers=auth_headers,
    )
    cancelled_replay = client.post(
        f"/projects/{project_id}/publication-jobs/{job2_id}/replay",
        headers=auth_headers,
    )
    assert cancelled_replay.status_code == 200
    assert cancelled_replay.json()["status"] == "queued"


# 11
def test_invariant_replay_does_not_auto_dispatch(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(
        client,
        auth_headers,
        project_id,
        channel_type="webhook",
        config={"url": "https://example.com/publish"},
    )
    asset_id = _draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)
    job_id = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    ).json()["id"]
    mock_fail = httpx.Response(500, request=httpx.Request("POST", "https://example.com"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_fail):
        for _ in range(3):
            client.post(
                f"/projects/{project_id}/publication-jobs/process",
                headers=auth_headers,
            )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        replay = client.post(
            f"/projects/{project_id}/publication-jobs/{job_id}/replay",
            headers=auth_headers,
        )
        assert replay.status_code == 200
        mock_post.assert_not_called()

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "queued"


# 12
def test_invariant_agents_have_no_publication_tools() -> None:
    registry = get_tool_registry()
    names = {tool.name for tool in registry.list_registered()}
    publication_related = {name for name in names if "publish" in name or "publication" in name}
    assert publication_related == set()
    for forbidden in FORBIDDEN_AGENT_TOOL_NAMES:
        assert forbidden not in names
    matrix = get_agent_tool_matrix(get_settings())
    for agent_row in matrix.values():
        for bucket in ("read", "write"):
            for tool_name in agent_row.get(bucket, []):
                lower = tool_name.lower()
                assert not any(fragment in lower for fragment in _PUBLICATION_TOOL_NAME_FRAGMENTS)


# 13
def test_invariant_tool_matrix_unchanged() -> None:
    path = Path(__file__).resolve().parents[1] / "app" / "agents" / "tool_matrix.py"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == FROZEN_TOOL_MATRIX_SHA256
    assert FORBIDDEN_AGENT_TOOL_NAMES == FROZEN_FORBIDDEN_AGENT_TOOL_NAMES


# 14
def test_invariant_health_exposes_publishing_flags_and_counts(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    ops = client.get("/health/operations")
    assert ops.status_code in (200, 503)
    body = ops.json()
    assert "publication_worker_enabled" in body
    assert "pending_publication_jobs_count" in body
    assert isinstance(body["pending_publication_jobs_count"], int)

    project_id = _project_id(client, auth_headers)
    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    )
    assert metrics.status_code == 200
    assert "publishing" in metrics.json()


# 15
def test_invariant_unsupported_channel_adapters_do_not_call_network(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _channel(
        client,
        auth_headers,
        project_id,
        channel_type="email",
        config={"smtp_host": "smtp.example.com", "smtp_user": "user"},
    )
    asset_id = _draft_asset(client, auth_headers, project_id)
    _approve_asset(client, auth_headers, project_id, asset_id)
    client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=auth_headers,
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        mock_post.assert_not_called()
