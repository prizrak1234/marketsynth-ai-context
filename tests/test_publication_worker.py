"""Phase 6.1 — publication worker, dispatcher, and delivery logs."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.agents.tool_matrix import FORBIDDEN_AGENT_TOOL_NAMES, get_agent_tool_matrix
from app.core.config import get_settings
from app.publishing.contracts import PublicationDeliveryLogStatus
from app.publishing.dispatch_result import PublicationDispatchResult
from app.publishing.dispatcher import PublicationDispatcher
from app.tools.registry import get_tool_registry
from app.workers.publication_worker import PublicationWorkerScheduler
from fastapi.testclient import TestClient


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Publication worker"},
        headers=headers,
    ).json()["id"]


def _create_custom_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
) -> str:
    response = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Custom noop", "type": "custom", "config": {}},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_telegram_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
) -> str:
    response = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "TG", "type": "telegram", "config": {"chat_id": "1"}},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_email_channel(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
) -> str:
    response = client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Email", "type": "email", "config": {"smtp_host": "smtp.example.com"}},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_draft_and_approve(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
) -> str:
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Pub", "body": "x"},
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


def _queue_job(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    asset_id: str,
    channel_id: str,
) -> str:
    response = client.post(
        f"/projects/{project_id}/publication-jobs",
        json={"asset_id": asset_id, "channel_id": channel_id},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_custom_noop_job_succeeds(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_custom_channel(client, auth_headers, project_id)
    asset_id = _create_draft_and_approve(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )

    batch = client.post(
        f"/projects/{project_id}/publication-jobs/process",
        headers=auth_headers,
    )
    assert batch.status_code == 200
    assert batch.json()["succeeded_count"] == 1

    job = client.get(
        f"/projects/{project_id}/publication-jobs/{job_id}",
        headers=auth_headers,
    ).json()
    assert job["status"] == "succeeded"
    assert job["finished_at"] is not None


def test_unsupported_channel_skipped_log_and_failed_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_email_channel(client, auth_headers, project_id)
    asset_id = _create_draft_and_approve(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )

    client.post(
        f"/projects/{project_id}/publication-jobs/process",
        headers=auth_headers,
    )

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
    assert len(logs) == 1
    assert logs[0]["status"] == "skipped"
    assert logs[0]["error_code"] == "unsupported_channel_adapter"


def test_delivery_log_on_success(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_custom_channel(client, auth_headers, project_id)
    asset_id = _create_draft_and_approve(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )
    client.post(
        f"/projects/{project_id}/publication-jobs/process",
        headers=auth_headers,
    )

    logs = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id, "status": "succeeded"},
        headers=auth_headers,
    ).json()
    assert len(logs) == 1
    assert logs[0]["attempt_number"] == 1
    assert "noop_dispatch" in (logs[0]["response_preview"] or "")


def test_delivery_log_on_dispatch_failure(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_custom_channel(client, auth_headers, project_id)
    asset_id = _create_draft_and_approve(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )

    async def _fail(*_args, **_kwargs):
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.FAILED,
            duration_ms=1,
            error_code="mock_failure",
            error_message="mock delivery failed",
        )

    with patch.object(PublicationDispatcher, "dispatch", new=_fail):
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )

    logs = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    assert logs[0]["status"] == "failed"
    assert logs[0]["error_code"] == "mock_failure"


@pytest.mark.asyncio
async def test_max_attempts_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PUBLICATION_JOB_MAX_ATTEMPTS", "3")
    get_settings.cache_clear()

    project_id = _project_id(client, auth_headers)
    channel_id = _create_custom_channel(client, auth_headers, project_id)
    asset_id = _create_draft_and_approve(client, auth_headers, project_id)
    job_id = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )

    async def _fail(*_args, **_kwargs):
        return PublicationDispatchResult(
            status=PublicationDeliveryLogStatus.FAILED,
            duration_ms=1,
            error_code="mock_failure",
            error_message="retryable failure",
        )

    with patch.object(PublicationDispatcher, "dispatch", new=_fail):
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

    logs = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": job_id},
        headers=auth_headers,
    ).json()
    assert len(logs) == 3

    get_settings.cache_clear()


def test_running_claim_prevents_double_processing(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_custom_channel(client, auth_headers, project_id)
    asset_id = _create_draft_and_approve(client, auth_headers, project_id)
    _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )

    first = client.post(
        f"/projects/{project_id}/publication-jobs/process",
        headers=auth_headers,
    ).json()
    second = client.post(
        f"/projects/{project_id}/publication-jobs/process",
        headers=auth_headers,
    ).json()
    assert first["processed_count"] == 1
    assert second["processed_count"] == 0


def test_process_endpoint_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/publication-jobs/process",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_delivery_logs_endpoint_filters(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    custom_id = _create_custom_channel(client, auth_headers, project_id)
    tg_id = _create_telegram_channel(client, auth_headers, project_id)
    asset_id = _create_draft_and_approve(client, auth_headers, project_id)
    custom_job = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=custom_id,
    )
    tg_job = _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=tg_id,
    )
    client.post(
        f"/projects/{project_id}/publication-jobs/process",
        headers=auth_headers,
    )

    by_channel = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"channel_id": custom_id},
        headers=auth_headers,
    ).json()
    assert len(by_channel) == 1
    assert by_channel[0]["publication_job_id"] == custom_job

    by_job = client.get(
        f"/projects/{project_id}/publication-deliveries",
        params={"job_id": tg_job, "status": "skipped"},
        headers=auth_headers,
    ).json()
    assert len(by_job) == 1


def test_worker_disabled_by_default() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.publication_worker_enabled is False

    scheduler = PublicationWorkerScheduler()
    import asyncio

    asyncio.run(scheduler.start())
    assert scheduler._task is None


def test_health_operations_includes_publication_worker_flag(client: TestClient) -> None:
    settings = get_settings()
    response = client.get("/health/operations")
    assert response.status_code in (200, 503)
    assert response.json()["publication_worker_enabled"] == settings.publication_worker_enabled


def test_no_external_http_on_process(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    channel_id = _create_custom_channel(client, auth_headers, project_id)
    asset_id = _create_draft_and_approve(client, auth_headers, project_id)
    _queue_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        client.post(
            f"/projects/{project_id}/publication-jobs/process",
            headers=auth_headers,
        )
        mock_post.assert_not_called()


def test_agent_tool_matrix_unchanged() -> None:
    matrix = get_agent_tool_matrix()
    assert "copywriter" in matrix
    registry = get_tool_registry()
    names = {tool.name for tool in registry.list_registered()}
    assert not any("publish" in name or "publication" in name for name in names)
    for forbidden in FORBIDDEN_AGENT_TOOL_NAMES:
        assert forbidden not in names
