"""Agent run logging API tests."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def _create_project(client: TestClient, headers: dict[str, str], name: str = "Run Project") -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_task(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/tasks",
        json={"project_id": project_id, "title": "Run task"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_run(
    client: TestClient,
    headers: dict[str, str],
    agent_id: str,
    *,
    task_id: str | None = None,
    input_payload: dict | None = None,
) -> dict:
    payload: dict = {
        "agent_id": agent_id,
        "input_payload": input_payload or {"prompt": "test"},
        "metadata": {"source": "pytest"},
    }
    if task_id is not None:
        payload["task_id"] = task_id
    response = client.post("/agent-runs", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_create_run_for_own_agent(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)
    assert run["agent_id"] == agent_id
    assert run["project_id"] == project_id
    assert run["status"] == "queued"
    assert run["metadata"] == {"source": "pytest"}


def test_cannot_create_run_for_foreign_agent(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    response = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {}},
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_cannot_create_run_for_archived_agent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    assert client.delete(f"/agents/{agent_id}", headers=auth_headers).status_code == 200

    response = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {}},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_task_id_must_match_agent_project(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_a = _create_project(client, auth_headers, name="Project A")
    project_b = _create_project(client, auth_headers, name="Project B")
    agent_id = _create_agent(client, auth_headers, project_a)
    task_b = _create_task(client, auth_headers, project_b)

    response = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "task_id": task_b, "input_payload": {}},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_runs_only_shows_current_user(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    own_run_id = _create_run(client, auth_headers, agent_id)["id"]

    other_project = _create_project(client, other_auth_headers, name="Other")
    other_agent = _create_agent(client, other_auth_headers, other_project)
    _create_run(client, other_auth_headers, other_agent)

    listed = client.get("/agent-runs", headers=auth_headers)
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert own_run_id in ids
    assert len(ids) == 1


def test_list_runs_filter_by_status(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_run(client, auth_headers, agent_id)["id"]

    assert (
        client.post(f"/agent-runs/{run_id}/running", headers=auth_headers).status_code == 200
    )

    queued = client.get("/agent-runs", params={"status": "queued"}, headers=auth_headers)
    running = client.get("/agent-runs", params={"status": "running"}, headers=auth_headers)
    assert all(item["id"] != run_id for item in queued.json())
    assert any(item["id"] == run_id for item in running.json())


def test_running_sets_started_at(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_run(client, auth_headers, agent_id)["id"]

    response = client.post(f"/agent-runs/{run_id}/running", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["started_at"] is not None
    assert body["finished_at"] is None


def test_succeeded_sets_finished_at_and_output(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_run(client, auth_headers, agent_id)["id"]

    response = client.post(
        f"/agent-runs/{run_id}/succeeded",
        json={"output_payload": {"result": "ok"}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"] == {"result": "ok"}
    assert body["finished_at"] is not None


def test_failed_sets_finished_at_and_error(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_run(client, auth_headers, agent_id)["id"]

    response = client.post(
        f"/agent-runs/{run_id}/failed",
        json={"error": "boom"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"] == "boom"
    assert body["finished_at"] is not None


def test_cancelled_sets_finished_at(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_run(client, auth_headers, agent_id)["id"]

    response = client.post(f"/agent-runs/{run_id}/cancelled", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["finished_at"] is not None


def test_foreign_run_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_run(client, auth_headers, agent_id)["id"]

    assert client.get(f"/agent-runs/{run_id}", headers=other_auth_headers).status_code == 404
    assert (
        client.post(f"/agent-runs/{run_id}/running", headers=other_auth_headers).status_code
        == 404
    )


def test_task_can_assign_agent_in_same_project(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    task_id = _create_task(client, auth_headers, project_id)

    response = client.patch(
        f"/tasks/{task_id}",
        json={"agent_id": agent_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["agent_id"] == agent_id


def test_task_cannot_assign_agent_from_other_project(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_a = _create_project(client, auth_headers, name="A")
    project_b = _create_project(client, auth_headers, name="B")
    agent_b = _create_agent(client, auth_headers, project_b)
    task_a = _create_task(client, auth_headers, project_a)

    response = client.patch(
        f"/tasks/{task_a}",
        json={"agent_id": agent_b},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_run_with_matching_task(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    task_id = _create_task(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id, task_id=task_id)
    assert run["task_id"] == task_id


def test_get_nonexistent_run_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    assert client.get(f"/agent-runs/{uuid4()}", headers=auth_headers).status_code == 404
