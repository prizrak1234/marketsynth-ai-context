"""Phase 3.11 — operational metrics and operations health."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.core.config import get_settings
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.queues.handoff_child_queue import handoff_queue_key
from app.schemas.contracts import AgentRunStatus, EventOutboxStatus, WebhookDeliveryLogStatus
from fastapi.testclient import TestClient

_PROCESS_HANDOFF = "/agent-runs/process-handoff-children"


def _patch_runner(store):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def _create_project(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post(
        "/projects",
        json={"name": name},
        headers=headers,
    ).json()["id"]


def test_project_metrics_requires_auth(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, "Auth gate")
    response = client.get(f"/projects/{project_id}/operational-metrics")
    assert response.status_code in (401, 403)


def test_project_metrics_enforces_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, "Metrics Own")
    response = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_counts_agent_runs_by_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, "Run counts")
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "metrics"}},
        headers=auth_headers,
    )
    body = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    assert body["window"] == "24h"
    assert sum(body["agent_runs"].values()) >= 1
    assert body["agent_runs"].get(AgentRunStatus.QUEUED.value, 0) >= 1


def test_counts_outbox_by_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, "Outbox metrics")
    orch = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator", "name": "O"},
        headers=auth_headers,
    ).json()["id"]
    res = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orch,
            "input_payload": {
                "prompt": "outbox metric",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    body = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    assert body["outbox"].get(EventOutboxStatus.PENDING.value, 0) >= 1


def test_counts_webhook_delivery_statuses_and_duration(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, "Webhook metrics")
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/metrics-hook?secret=hide"},
        headers=auth_headers,
    )
    orch = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator", "name": "O"},
        headers=auth_headers,
    ).json()["id"]
    res = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orch,
            "input_payload": {
                "prompt": "delivery metric",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
            },
        },
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    ok = httpx.Response(200, request=httpx.Request("POST", "https://example.com/metrics-hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=ok):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    body = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    delivery = body["webhooks"]["delivery_status"]
    assert delivery.get(WebhookDeliveryLogStatus.SUCCEEDED.value, 0) >= 1
    assert body["webhooks"]["avg_duration_ms"] is not None
    assert body["webhooks"]["max_duration_ms"] is not None


def test_oldest_pending_outbox_age_exists(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, "Outbox age")
    orch = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator", "name": "O"},
        headers=auth_headers,
    ).json()["id"]
    res = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orch,
            "input_payload": {
                "prompt": "age",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
            },
        },
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    body = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    assert body["outbox"]["oldest_pending_age_seconds"] is not None
    assert body["outbox"]["oldest_pending_age_seconds"] >= 0


def test_redis_queue_depth_when_available(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_redis: object,
) -> None:
    from uuid import UUID

    from app.core.redis import get_redis

    asyncio.run(get_redis().flushall())
    project_id = _create_project(client, auth_headers, "Redis depth")
    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    owner_id = UUID(project["owner_id"])
    # enqueue via handoff flow
    orch = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator", "name": "O"},
        headers=auth_headers,
    ).json()["id"]
    res = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orch,
            "input_payload": {
                "prompt": "queue depth",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
            },
        },
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)

    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    assert metrics["redis"]["available"] is True
    assert metrics["redis"]["queue_depth"] >= 0
    assert asyncio.run(get_redis().llen(handoff_queue_key(owner_id))) >= 0


def test_redis_failure_does_not_break_endpoint(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers, "Redis fail")

    async def _boom(_owner_id: object) -> int:
        raise ConnectionError("redis down")

    monkeypatch.setattr(
        "app.queues.handoff_queue_metrics.get_owner_queue_depth",
        _boom,
    )
    response = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["redis"]["available"] is False
    assert body["redis"]["error"]


def test_health_operations_returns_scheduler_flags(client: TestClient) -> None:
    response = client.get("/health/operations")
    assert response.status_code in (200, 503)
    body = response.json()
    settings = get_settings()
    assert body["handoff_scheduler_enabled"] == settings.graph_handoff_scheduler_enabled
    assert body["outbox_dispatcher_enabled"] == settings.event_outbox_dispatcher_enabled
    assert body["publication_worker_enabled"] == settings.publication_worker_enabled
    assert body["graph_version"] == settings.graph_version
    assert "pending_outbox_count" in body
    assert "pending_publication_jobs_count" in body
    assert "handoff_queue_known_owners_count" in body


def test_metrics_response_has_no_secrets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, "No secrets")
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://hooks.example.com/path?token=secret"},
        headers=auth_headers,
    )
    body = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    serialized = str(body).lower()
    assert "bwhsec" not in serialized
    assert "token=secret" not in serialized
    assert "https://hooks.example.com" not in serialized


def test_classic_executor_unaffected(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_ENGINE", "classic")
    get_settings.cache_clear()
    project_id = _create_project(client, auth_headers, "Classic")
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "classic dry"}},
        headers=auth_headers,
    ).json()["id"]
    response = client.post(
        f"/agent-runs/{run}/execute-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == AgentRunStatus.SUCCEEDED.value
