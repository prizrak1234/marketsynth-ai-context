"""Phase 3.6 — handoff child run worker."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.core.config import get_settings
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.graphs.handoff import is_handoff_child_run
from app.workers.handoff_child_worker import HandoffChildRunWorker
from fastapi.testclient import TestClient


def test_is_handoff_child_run_detects_metadata() -> None:
    assert is_handoff_child_run(
        {
            "parent_agent_run_id": "abc",
            "execution_engine": "langgraph-handoff-child",
        },
    )
    assert not is_handoff_child_run({"execution_engine": "langgraph-dry-run"})


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Worker Project"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_type: str,
    name: str,
) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": agent_type, "name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_run(
    client: TestClient,
    headers: dict[str, str],
    agent_id: str,
    *,
    input_payload: dict,
    metadata: dict | None = None,
) -> dict:
    response = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": input_payload,
            "metadata": metadata or {},
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _patch_runner_with_store(store: InMemoryGraphCheckpointStore):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def test_worker_processes_queued_handoff_child(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client, auth_headers, project_id, agent_type="orchestrator", name="Orch"
    )
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    run = _create_run(
        client,
        auth_headers,
        orchestrator_id,
        input_payload={
            "prompt": "delegate to worker",
            "handoff_to_agent_id": researcher_id,
            "handoff_enqueue_child": True,
            "handoff_execute_child": False,
        },
    )

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        parent_resp = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert parent_resp.status_code == 200
    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    child_id = parent["output_payload"]["handoff"]["child_run_id"]
    assert parent["output_payload"]["handoff"]["child_run_pending_worker"] is True

    child_before = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child_before["status"] == "queued"

    with _patch_runner_with_store(store):
        worker_resp = client.post(
            "/agent-runs/process-handoff-children",
            headers=auth_headers,
            params={"limit": 5},
        )
    assert worker_resp.status_code == 200
    body = worker_resp.json()
    assert body["processed_count"] >= 1
    assert any(
        item["run_id"] == child_id and item["processed"] and item["status"] == "succeeded"
        for item in body["results"]
    )

    child_after = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child_after["status"] == "succeeded"


def test_worker_skips_non_handoff_queued_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id, agent_type="researcher", name="Solo")
    run = _create_run(client, auth_headers, agent_id, input_payload={"prompt": "normal queued"})
    response = client.post(
        "/agent-runs/process-handoff-children",
        headers=auth_headers,
        params={"limit": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["processed_count"] == 0
    assert body["results"] == []
    still_queued = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert still_queued["status"] == "queued"


def test_handoff_chain_allowed_at_depth_one_when_max_depth_two(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAPH_HANDOFF_MAX_DEPTH", "2")
    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    copywriter_id = _create_agent(
        client, auth_headers, project_id, agent_type="copywriter", name="Copy"
    )
    run = _create_run(
        client,
        auth_headers,
        researcher_id,
        input_payload={
            "prompt": "chain handoff",
            "handoff_to_agent_id": copywriter_id,
        },
        metadata={"handoff_depth": 1},
    )
    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    get_settings.cache_clear()


def test_handoff_chain_blocked_at_max_depth(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    researcher_id = _create_agent(
        client, auth_headers, project_id, agent_type="researcher", name="Res"
    )
    copywriter_id = _create_agent(
        client, auth_headers, project_id, agent_type="copywriter", name="Copy"
    )
    run = _create_run(
        client,
        auth_headers,
        researcher_id,
        input_payload={
            "prompt": "too deep",
            "handoff_to_agent_id": copywriter_id,
        },
        metadata={"handoff_depth": 2},
    )
    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 500
    assert "handoff_max_depth_exceeded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_worker_list_pending_filters_handoff_children(
    db_session,
) -> None:
    from app.db.models.user import UserTable
    from app.db.repositories.user_repo import UserRepository
    from app.schemas.contracts import AgentRunStatus, AgentType
    from app.schemas.crud import AgentCreateRequest, ProjectCreate
    from app.services.agent_runs import AgentRunService
    from app.services.agents import AgentService
    from app.services.projects_service import ProjectService

    owner = await UserRepository(db_session).create(UserTable(telegram_id=9401))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Worker Filter"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(
            project_id=project.id,
            type=AgentType.RESEARCHER,
            name="Filter Agent",
        ),
    )
    assert agent is not None
    service = AgentRunService(db_session)
    handoff_row = await service.create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "x"},
        metadata={
            "parent_agent_run_id": str(owner.id),
            "execution_engine": "langgraph-handoff-child",
        },
    )
    assert handoff_row is not None
    normal_row = await service.create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "y"},
        metadata={},
    )
    assert normal_row is not None

    worker = HandoffChildRunWorker(db_session)
    pending = await worker.list_pending(owner.id, limit=10)
    pending_ids = {row.id for row in pending}
    assert handoff_row.id in pending_ids
    assert normal_row.id not in pending_ids
    assert all(row.status == AgentRunStatus.QUEUED for row in pending)
