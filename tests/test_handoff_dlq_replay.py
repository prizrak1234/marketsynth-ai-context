"""Phase 3.10 — handoff DLQ child replay."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from app.core.config import get_settings
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.queues.handoff_child_queue import handoff_queue_key
from fastapi.testclient import TestClient

_PROCESS_HANDOFF = "/agent-runs/process-handoff-children"


def _patch_runner(store):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def _dead_letter_child(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict, str, str]:
    monkeypatch.setenv("GRAPH_HANDOFF_MAX_ATTEMPTS", "1")
    get_settings.cache_clear()

    project_id = client.post(
        "/projects", json={"name": "DLQ Replay"}, headers=auth_headers,
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
                "prompt": "dlq replay",
                "handoff_to_agent_id": res,
                "handoff_enqueue_child": True,
                "handoff_execute_child": False,
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
            "always_fail",
        ),
    ):
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    child_id = parent["output_payload"]["handoff"]["child_run_id"]
    return parent, child_id, project_id


def test_replay_dead_lettered_child_resets_and_requeues(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from uuid import UUID

    from app.core.redis import get_redis

    asyncio.run(get_redis().flushall())
    parent, child_id, _project_id = _dead_letter_child(client, auth_headers, monkeypatch)
    owner_uuid = UUID(parent["owner_id"])

    response = client.post(f"/agent-runs/{child_id}/handoff/replay", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["replayed"] is True
    assert body["status"] == "queued"

    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child["status"] == "queued"
    assert child["metadata"]["handoff_worker"]["dead_lettered"] is False
    assert child["metadata"]["handoff_worker"]["attempts"] == 0

    assert asyncio.run(get_redis().llen(handoff_queue_key(owner_uuid))) == 1

    parent_after = client.get(f"/agent-runs/{parent['id']}", headers=auth_headers).json()
    handoff = parent_after["output_payload"]["handoff"]
    assert handoff["child_run_status"] == "queued"
    assert handoff["child_run_pending_worker"] is True
    assert handoff["child_run_executed"] is False


def test_replay_rejects_succeeded_child(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects", json={"name": "No Replay"}, headers=auth_headers,
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
    ).json()
    store = InMemoryGraphCheckpointStore()
    with _patch_runner(store):
        client.post(f"/agent-runs/{run['id']}/execute-graph-dry-run", headers=auth_headers)

    response = client.post(f"/agent-runs/{run['id']}/handoff/replay", headers=auth_headers)
    assert response.status_code == 409


def test_replay_rejects_other_owner(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _parent, child_id, _project_id = _dead_letter_child(client, auth_headers, monkeypatch)
    response = client.post(f"/agent-runs/{child_id}/handoff/replay", headers=other_auth_headers)
    assert response.status_code == 404
