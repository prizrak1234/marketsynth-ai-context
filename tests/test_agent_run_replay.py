"""Phase 3.15 — AgentRun clone replay policy."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.core.config import get_settings
from fastapi.testclient import TestClient


def _create_project_agent(
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    with_task: bool = False,
) -> tuple[str, str, str | None]:
    project_id = client.post(
        "/projects",
        json={"name": "Replay project"},
        headers=auth_headers,
    ).json()["id"]
    task_id: str | None = None
    if with_task:
        task_id = client.post(
            "/tasks",
            json={"project_id": project_id, "title": "Replay task"},
            headers=auth_headers,
        ).json()["id"]
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher", "name": "Replay agent"},
        headers=auth_headers,
    ).json()["id"]
    return project_id, agent_id, task_id


def _create_run(
    client: TestClient,
    auth_headers: dict[str, str],
    agent_id: str,
    *,
    task_id: str | None = None,
    input_payload: dict | None = None,
) -> str:
    body: dict = {
        "agent_id": agent_id,
        "input_payload": input_payload or {"prompt": "replay me"},
    }
    if task_id is not None:
        body["task_id"] = task_id
    return client.post("/agent-runs", json=body, headers=auth_headers).json()["id"]


def _mark_failed(client: TestClient, auth_headers: dict[str, str], run_id: str) -> None:
    client.post(
        f"/agent-runs/{run_id}/failed",
        json={"error": "provider timeout"},
        headers=auth_headers,
    )


def _mark_cancelled(client: TestClient, auth_headers: dict[str, str], run_id: str) -> None:
    client.post(f"/agent-runs/{run_id}/cancelled", headers=auth_headers)


def test_failed_run_can_be_replayed_into_new_queued_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)

    response = client.post(
        f"/agent-runs/{source_id}/replay",
        json={"reason": "manual_retry_after_provider_failure"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    clone = response.json()
    assert clone["id"] != source_id
    assert clone["status"] == "queued"
    assert clone["metadata"]["replay"]["source_run_id"] == source_id
    assert clone["metadata"]["replay"]["source_status"] == "failed"
    assert clone["metadata"]["replay"]["reason"] == "manual_retry_after_provider_failure"


def test_cancelled_run_can_be_replayed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_cancelled(client, auth_headers, source_id)

    response = client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    assert response.json()["metadata"]["replay"]["source_status"] == "cancelled"


@pytest.mark.parametrize(
    "terminal_action",
    ["succeeded", "running", "queued"],
)
def test_non_replayable_statuses_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    terminal_action: str,
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    run_id = _create_run(client, auth_headers, agent_id)

    if terminal_action == "succeeded":
        client.post(
            f"/agent-runs/{run_id}/succeeded",
            json={"output_payload": {"answer": "ok"}},
            headers=auth_headers,
        )
    elif terminal_action == "running":
        client.post(f"/agent-runs/{run_id}/running", headers=auth_headers)
    else:
        pass

    response = client.post(f"/agent-runs/{run_id}/replay", headers=auth_headers)
    assert response.status_code == 409
    assert "agent_run_not_replayable" in response.json()["detail"]


def test_replay_enforces_ownership(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)

    response = client.post(
        f"/agent-runs/{source_id}/replay",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_replay_rejects_archived_agent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)
    client.delete(f"/agents/{agent_id}", headers=auth_headers)

    response = client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers)
    assert response.status_code == 409
    assert "agent_archived_replay_forbidden" in response.json()["detail"]


def test_replay_copies_input_payload(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    payload = {"prompt": "copy this", "extra": 42}
    source_id = _create_run(client, auth_headers, agent_id, input_payload=payload)
    _mark_failed(client, auth_headers, source_id)

    clone = client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers).json()
    assert clone["input_payload"] == payload


def test_replay_copies_task_id(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, task_id = _create_project_agent(client, auth_headers, with_task=True)
    source_id = _create_run(client, auth_headers, agent_id, task_id=task_id)
    _mark_failed(client, auth_headers, source_id)

    clone = client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers).json()
    assert clone["task_id"] == task_id


def test_replay_does_not_copy_output_error_or_timestamps(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    client.post(f"/agent-runs/{source_id}/running", headers=auth_headers)
    _mark_failed(client, auth_headers, source_id)
    source = client.get(f"/agent-runs/{source_id}", headers=auth_headers).json()

    clone = client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers).json()
    assert clone.get("output_payload") is None
    assert clone.get("error") is None
    assert clone.get("started_at") is None
    assert clone.get("finished_at") is None
    assert source["status"] == "failed"
    assert source["error"] == "provider timeout"
    assert source.get("started_at") is not None


def test_replay_metadata_links_source_run_id(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)

    replay_body = client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers).json()
    replay_meta = replay_body["metadata"]["replay"]
    assert replay_meta["source_run_id"] == source_id
    assert replay_meta["created_at"]


def test_replay_endpoint_does_not_auto_execute(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)

    coord_path = "app.executors.agent_run_coordinator.AgentRunCoordinator.execute_run"
    with patch(coord_path) as execute_mock:
        clone_id = client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers).json()["id"]
        execute_mock.assert_not_called()

    assert client.get(f"/agent-runs/{clone_id}", headers=auth_headers).json()["status"] == "queued"


def test_replayed_run_can_be_executed_via_unified_execute(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_EXECUTION_FORCE_CLASSIC", "true")
    get_settings.cache_clear()
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)

    clone_id = client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers).json()["id"]
    executed = client.post(f"/agent-runs/{clone_id}/execute", headers=auth_headers)
    assert executed.status_code == 200
    assert executed.json()["status"] == "succeeded"


def test_source_run_remains_unchanged(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)
    before = client.get(f"/agent-runs/{source_id}", headers=auth_headers).json()

    client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers)
    after = client.get(f"/agent-runs/{source_id}", headers=auth_headers).json()

    assert after == before


def test_operational_metrics_count_replays(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)
    client.post(f"/agent-runs/{source_id}/replay", headers=auth_headers)

    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    assert metrics["replay"]["replayed_runs_count"] >= 1
    assert metrics["replay"]["failed_runs_replayed_count"] >= 1
    assert metrics["replay"]["replay_source_status_counts"].get("failed", 0) >= 1


def test_replay_reason_too_long_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    _project_id, agent_id, _task_id = _create_project_agent(client, auth_headers)
    source_id = _create_run(client, auth_headers, agent_id)
    _mark_failed(client, auth_headers, source_id)

    response = client.post(
        f"/agent-runs/{source_id}/replay",
        json={"reason": "x" * 300},
        headers=auth_headers,
    )
    assert response.status_code == 422
