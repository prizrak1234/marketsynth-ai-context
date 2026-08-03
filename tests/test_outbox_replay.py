"""Phase 3.10 — outbox dead-letter and replay."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
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


def _handoff_event_setup(client: TestClient, auth_headers: dict[str, str]) -> tuple[str, str]:
    project_id = client.post(
        "/projects", json={"name": "Outbox Replay"}, headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/webhooks",
        json={"url": "https://example.com/replay-hook"},
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
                "prompt": "outbox replay",
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
    events = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.PENDING.value},
    ).json()
    return project_id, events[0]["id"]


def test_event_becomes_dead_lettered_after_max_attempts(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_OUTBOX_DISPATCH_MAX_ATTEMPTS", "2")
    from app.core.config import get_settings

    get_settings.cache_clear()
    project_id, event_id = _handoff_event_setup(client, auth_headers)
    fail_resp = httpx.Response(500, request=httpx.Request("POST", "https://example.com/replay-hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fail_resp):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    dead = client.get(
        f"/projects/{project_id}/events",
        headers=auth_headers,
        params={"status": EventOutboxStatus.DEAD_LETTERED.value},
    ).json()
    assert len(dead) >= 1
    assert dead[0]["id"] == event_id


def test_replay_resets_dead_lettered_event_to_pending(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_OUTBOX_DISPATCH_MAX_ATTEMPTS", "1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    project_id, event_id = _handoff_event_setup(client, auth_headers)
    fail_resp = httpx.Response(500, request=httpx.Request("POST", "https://example.com/replay-hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=fail_resp):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    replay = client.post(
        f"/projects/{project_id}/events/{event_id}/replay",
        headers=auth_headers,
    )
    assert replay.status_code == 200
    body = replay.json()
    assert body["replayed"] is True
    assert body["status"] == EventOutboxStatus.PENDING.value

    ok_resp = httpx.Response(200, request=httpx.Request("POST", "https://example.com/replay-hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=ok_resp):
        dispatch = client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)
    assert dispatch.json()["dispatched_count"] >= 1


def test_replay_rejects_sent_event(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, event_id = _handoff_event_setup(client, auth_headers)
    ok_resp = httpx.Response(200, request=httpx.Request("POST", "https://example.com/replay-hook"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=ok_resp):
        client.post(f"/projects/{project_id}/events/dispatch", headers=auth_headers)

    response = client.post(
        f"/projects/{project_id}/events/{event_id}/replay",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_replay_rejects_other_owner_event(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id, event_id = _handoff_event_setup(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/events/{event_id}/replay",
        headers=other_auth_headers,
    )
    assert response.status_code == 404
