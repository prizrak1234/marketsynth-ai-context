"""LLM request/response logging API tests."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def _create_project(client: TestClient, headers: dict[str, str], name: str = "LLM Project") -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "copywriter"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent_run(client: TestClient, headers: dict[str, str], agent_id: str) -> str:
    response = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"step": "llm"}},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_llm_request(
    client: TestClient,
    headers: dict[str, str],
    agent_run_id: str,
    *,
    provider: str = "mock",
    model: str = "mock-gpt",
) -> dict:
    response = client.post(
        "/llm-requests",
        json={
            "agent_run_id": agent_run_id,
            "provider": provider,
            "model": model,
            "input_payload": {"messages": [{"role": "user", "content": "hi"}]},
            "prompt_metadata": {"template": "v1"},
            "request_metadata": {"source": "pytest"},
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_llm_request_for_own_agent_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    body = _create_llm_request(client, auth_headers, run_id)
    assert body["agent_run_id"] == run_id
    assert body["agent_id"] == agent_id
    assert body["project_id"] == project_id
    assert body["provider"] == "mock"
    assert body["status"] == "queued"


def test_cannot_create_llm_request_for_foreign_agent_run(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    response = client.post(
        "/llm-requests",
        json={"agent_run_id": run_id, "provider": "mock", "model": "mock-gpt"},
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_list_llm_requests_filter_by_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]
    assert (
        client.post(f"/llm-requests/{request_id}/running", headers=auth_headers).status_code
        == 200
    )

    queued = client.get("/llm-requests", params={"status": "queued"}, headers=auth_headers)
    running = client.get("/llm-requests", params={"status": "running"}, headers=auth_headers)
    assert all(item["id"] != request_id for item in queued.json())
    assert any(item["id"] == request_id for item in running.json())


def test_list_llm_requests_filter_by_provider(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(
        client,
        auth_headers,
        run_id,
        provider="openai",
        model="gpt-4.1-mini",
    )["id"]

    openai = client.get("/llm-requests", params={"provider": "openai"}, headers=auth_headers)
    mock = client.get("/llm-requests", params={"provider": "mock"}, headers=auth_headers)
    assert any(item["id"] == request_id for item in openai.json())
    assert all(item["id"] != request_id for item in mock.json())


def test_foreign_llm_request_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]

    assert client.get(f"/llm-requests/{request_id}", headers=other_auth_headers).status_code == 404


def test_running_sets_started_at(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]

    response = client.post(f"/llm-requests/{request_id}/running", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["started_at"] is not None


def test_succeeded_creates_response(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]

    response = client.post(
        f"/llm-requests/{request_id}/succeeded",
        json={
            "output_payload": {"text": "hello"},
            "raw_response": {"mock": True},
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "latency_ms": 42,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["request"]["status"] == "succeeded"
    assert detail["request"]["finished_at"] is not None
    assert detail["response"]["output_payload"] == {"text": "hello"}
    assert detail["response"]["total_tokens"] == 15


def test_failed_stores_error(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]

    response = client.post(
        f"/llm-requests/{request_id}/failed",
        json={"error": "provider timeout"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"] == "provider timeout"
    assert body["finished_at"] is not None


def test_cancelled_sets_finished_at(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]

    response = client.post(f"/llm-requests/{request_id}/cancelled", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["finished_at"] is not None


def test_cannot_succeed_after_failed(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]
    assert (
        client.post(
            f"/llm-requests/{request_id}/failed",
            json={"error": "boom"},
            headers=auth_headers,
        ).status_code
        == 200
    )

    response = client.post(
        f"/llm-requests/{request_id}/succeeded",
        json={"output_payload": {"text": "nope"}},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_cannot_create_second_response(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]
    assert (
        client.post(
            f"/llm-requests/{request_id}/succeeded",
            json={"output_payload": {"text": "once"}},
            headers=auth_headers,
        ).status_code
        == 200
    )

    response = client.post(
        f"/llm-requests/{request_id}/succeeded",
        json={"output_payload": {"text": "twice"}},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_task_id_must_match_agent_run(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_a = _create_project(client, auth_headers, name="A")
    project_b = _create_project(client, auth_headers, name="B")
    agent_a = _create_agent(client, auth_headers, project_a)
    run_a = _create_agent_run(client, auth_headers, agent_a)
    task_b = client.post(
        "/tasks",
        json={"project_id": project_b, "title": "Other task"},
        headers=auth_headers,
    ).json()["id"]

    response = client.post(
        "/llm-requests",
        json={
            "agent_run_id": run_a,
            "task_id": task_b,
            "provider": "mock",
            "model": "mock-gpt",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_archived_agent_does_not_block_llm_logging(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    assert client.delete(f"/agents/{agent_id}", headers=auth_headers).status_code == 200

    body = _create_llm_request(client, auth_headers, run_id)
    assert body["agent_id"] == agent_id
    assert body["agent_run_id"] == run_id


def test_get_llm_request_includes_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run_id = _create_agent_run(client, auth_headers, agent_id)
    request_id = _create_llm_request(client, auth_headers, run_id)["id"]
    client.post(
        f"/llm-requests/{request_id}/succeeded",
        json={"output_payload": {"text": "done"}},
        headers=auth_headers,
    )

    detail = client.get(f"/llm-requests/{request_id}", headers=auth_headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["response"] is not None
    assert payload["response"]["output_payload"] == {"text": "done"}


def test_get_nonexistent_llm_request_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    assert client.get(f"/llm-requests/{uuid4()}", headers=auth_headers).status_code == 404
