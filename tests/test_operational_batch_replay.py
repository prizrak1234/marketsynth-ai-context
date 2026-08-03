"""Phase 3.12 — batch replay and delivery log cleanup."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.db.base import utc_now
from app.db.repositories.webhook_delivery_logs import WebhookDeliveryLogRepository
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.queues.handoff_child_queue import handoff_queue_key
from app.schemas.contracts import EventOutboxStatus
from fastapi.testclient import TestClient

_PROCESS_HANDOFF = "/agent-runs/process-handoff-children"


def _patch_runner(store):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def _handoff_outbox_setup(client: TestClient, auth_headers: dict[str, str]) -> tuple[str, str]:
    project_id = client.post(
        "/projects", json={"name": "Batch Outbox"}, headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/batch-hook"},
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
                "prompt": "batch outbox",
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
    events = client.get(f"/projects/{project_id}/events", headers=auth_headers).json()
    return project_id, events[0]["id"]


def test_batch_outbox_replay_resets_dead_lettered(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_OUTBOX_DISPATCH_MAX_ATTEMPTS", "1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    project_id, _event_id = _handoff_outbox_setup(client, auth_headers)
    fail_resp = httpx.Response(500, request=httpx.Request("POST", "https://example.com/batch-hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fail_resp):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    batch = client.post(
        f"/projects/{project_id}/events/replay-batch",
        headers=auth_headers,
        json={
            "statuses": ["failed", "dead_lettered"],
            "limit": 50,
        },
    )
    assert batch.status_code == 200
    body = batch.json()
    assert body["replayed_count"] >= 1
    pending = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.PENDING.value},
    ).json()
    assert len(pending) >= 1


def test_batch_outbox_replay_skips_sent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, event_id = _handoff_outbox_setup(client, auth_headers)
    ok_resp = httpx.Response(200, request=httpx.Request("POST", "https://example.com/batch-hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=ok_resp):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    sent = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.SENT.value},
    ).json()
    assert sent[0]["id"] == event_id

    batch = client.post(
        f"/projects/{project_id}/events/replay-batch",
        headers=auth_headers,
        json={"statuses": ["failed", "dead_lettered"], "limit": 50},
    ).json()
    assert batch["replayed_count"] == 0
    assert client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.SENT.value},
    ).json()[0]["status"] == "sent"


def test_batch_outbox_replay_enforces_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id, _ = _handoff_outbox_setup(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/events/replay-batch",
        headers=other_auth_headers,
        json={"statuses": ["dead_lettered"], "limit": 10},
    )
    assert response.status_code == 404


def test_batch_outbox_replay_limit_validation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, _ = _handoff_outbox_setup(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/events/replay-batch",
        headers=auth_headers,
        json={"statuses": ["failed"], "limit": 101},
    )
    assert response.status_code == 422


def test_batch_handoff_replay_requeues_children(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import UUID

    from app.core.config import get_settings
    from app.core.redis import get_redis

    monkeypatch.setenv("GRAPH_HANDOFF_MAX_ATTEMPTS", "1")
    get_settings.cache_clear()
    asyncio.run(get_redis().flushall())

    project_id = client.post(
        "/projects", json={"name": "Batch Handoff"}, headers=auth_headers,
    ).json()["id"]
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
                "prompt": "batch handoff",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
            },
        },
        headers=auth_headers,
    ).json()
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run['id']}/execute-graph-dry-run", headers=auth_headers)
    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=__import__("app.core.exceptions", fromlist=["ExecutorError"]).ExecutorError(
            "batch_fail",
        ),
    ):
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    owner_id = UUID(parent["owner_id"])

    batch = client.post(
        "/agent-runs/handoff/replay-batch",
        headers=auth_headers,
        json={"project_id": project_id, "limit": 50},
    )
    assert batch.status_code == 200
    assert batch.json()["requeued_count"] >= 1
    assert asyncio.run(get_redis().llen(handoff_queue_key(owner_id))) >= 1


def test_batch_handoff_replay_skips_succeeded_child(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Skip succeeded"}, headers=auth_headers,
    ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "R"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "solo"}},
        headers=auth_headers,
    ).json()["id"]
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run}/execute-graph-dry-run", headers=auth_headers)

    batch = client.post(
        "/agent-runs/handoff/replay-batch",
        headers=auth_headers,
        json={"project_id": project_id, "limit": 50},
    ).json()
    assert batch["requeued_count"] == 0


def test_batch_handoff_replay_updates_parent_summary(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("GRAPH_HANDOFF_MAX_ATTEMPTS", "1")
    get_settings.cache_clear()

    project_id = client.post(
        "/projects", json={"name": "Parent batch"}, headers=auth_headers,
    ).json()["id"]
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
                "prompt": "parent batch",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
            },
        },
        headers=auth_headers,
    ).json()
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run['id']}/execute-graph-dry-run", headers=auth_headers)
    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=__import__("app.core.exceptions", fromlist=["ExecutorError"]).ExecutorError(
            "fail",
        ),
    ):
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    client.post(
        "/agent-runs/handoff/replay-batch",
        headers=auth_headers,
        json={"project_id": project_id, "limit": 50},
    )
    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    handoff = parent["output_payload"]["handoff"]
    assert handoff["child_run_status"] == "queued"
    assert handoff["child_run_pending_worker"] is True
    assert handoff["child_run_executed"] is False


def test_cleanup_deletes_only_old_delivery_logs(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: object,
) -> None:
    from uuid import UUID, uuid4

    from app.db.models.webhook_delivery_log import WebhookDeliveryLogTable
    from app.schemas.contracts import WebhookDeliveryLogStatus

    project_id = client.post(
        "/projects", json={"name": "Cleanup"}, headers=auth_headers,
    ).json()["id"]
    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    owner_id = UUID(project["owner_id"])
    project_uuid = UUID(project_id)
    event_id = uuid4()

    old_row = WebhookDeliveryLogTable(
        owner_id=owner_id,
        project_id=project_uuid,
        event_outbox_id=event_id,
        event_type="graph.handoff.parent_synced",
        target_url_preview="https://example.com/old",
        status=WebhookDeliveryLogStatus.SUCCEEDED,
        attempt_number=1,
        created_at=utc_now() - timedelta(days=40),
    )
    new_row = WebhookDeliveryLogTable(
        owner_id=owner_id,
        project_id=project_uuid,
        event_outbox_id=event_id,
        event_type="graph.handoff.parent_synced",
        target_url_preview="https://example.com/new",
        status=WebhookDeliveryLogStatus.SUCCEEDED,
        attempt_number=1,
        created_at=utc_now() - timedelta(days=1),
    )

    async def _seed() -> None:
        repo = WebhookDeliveryLogRepository(db_session)
        await repo.create(old_row)
        await repo.create(new_row)
        await db_session.commit()

    asyncio.run(_seed())

    response = client.delete(
        f"/projects/{project_id}/webhook-deliveries/cleanup",
        headers=auth_headers,
        params={"older_than_days": 30},
    )
    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1

    remaining = client.get(
        f"/projects/{project_id}/webhook-deliveries",
        headers=auth_headers,
    ).json()
    assert len(remaining) == 1
    assert remaining[0]["target_url_preview"] == "https://example.com/new"


def test_cleanup_rejects_older_than_days_below_min(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Cleanup min"}, headers=auth_headers,
    ).json()["id"]
    response = client.delete(
        f"/projects/{project_id}/webhook-deliveries/cleanup",
        headers=auth_headers,
        params={"older_than_days": 3},
    )
    assert response.status_code == 422


def test_cleanup_response_has_no_secrets(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Cleanup secrets"}, headers=auth_headers,
    ).json()["id"]
    response = client.delete(
        f"/projects/{project_id}/webhook-deliveries/cleanup",
        headers=auth_headers,
        params={"older_than_days": 30},
    ).json()
    assert set(response.keys()) <= {"deleted_count", "older_than_days"}
    assert "bwhsec" not in str(response).lower()


def test_single_replay_endpoints_still_work(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("EVENT_OUTBOX_DISPATCH_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("GRAPH_HANDOFF_MAX_ATTEMPTS", "1")
    get_settings.cache_clear()

    project_id = client.post(
        "/projects", json={"name": "Single replay"}, headers=auth_headers,
    ).json()["id"]
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
                "prompt": "single",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
            },
        },
        headers=auth_headers,
    ).json()
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run['id']}/execute-graph-dry-run", headers=auth_headers)
    with patch(
        "app.workers.handoff_child_worker.execute_handoff_child_run",
        side_effect=__import__("app.core.exceptions", fromlist=["ExecutorError"]).ExecutorError(
            "fail",
        ),
    ):
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    child_id = parent["output_payload"]["handoff"]["child_run_id"]
    assert client.post(
        f"/agent-runs/{child_id}/handoff/replay",
        headers=auth_headers,
    ).status_code == 200

    fail_resp = httpx.Response(500, request=httpx.Request("POST", "https://example.com/x"))
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/x"},
        headers=auth_headers,
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fail_resp):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)
    event_id = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.DEAD_LETTERED.value},
    ).json()[0]["id"]
    assert client.post(
        f"/projects/{project_id}/events/{event_id}/replay",
        headers=auth_headers,
    ).status_code == 200
