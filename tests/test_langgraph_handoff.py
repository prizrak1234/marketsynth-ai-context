"""Phase 3.4 — graph multi-agent handoff skeleton."""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from app.graphs.agent_graph import build_agent_graph
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.graphs.handoff import (
    HANDOFF_STATUS_DELEGATED,
    HANDOFF_STATUS_NONE,
    evaluate_graph_handoff,
    extract_handoff_controls,
    is_handoff_allowed,
)
from app.schemas.contracts import AgentType
from fastapi.testclient import TestClient


def test_agent_graph_includes_handoff_nodes() -> None:
    nodes = set(build_agent_graph().nodes.keys())
    assert {"handoff_gate", "handoff_record"}.issubset(nodes)


def test_orchestrator_may_handoff_to_researcher() -> None:
    assert is_handoff_allowed(AgentType.ORCHESTRATOR, AgentType.RESEARCHER)


def test_researcher_may_not_handoff_to_orchestrator() -> None:
    assert not is_handoff_allowed(AgentType.RESEARCHER, AgentType.ORCHESTRATOR)


def test_extract_handoff_controls_strips_keys() -> None:
    target_id = uuid4()
    cleaned, request, type_hint = extract_handoff_controls(
        {
            "prompt": "delegate",
            "handoff_to_agent_id": str(target_id),
            "handoff_reason": "need research",
        },
    )
    assert cleaned == {"prompt": "delegate"}
    assert type_hint is None
    assert request is not None
    assert request.target_agent_id == target_id
    assert request.reason == "need research"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Handoff Project"}, headers=headers)
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
    from unittest.mock import patch

    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def test_graph_handoff_delegates_without_running_source_llm(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orchestrator",
    )
    researcher_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher",
    )
    run = _create_run(
        client,
        auth_headers,
        orchestrator_id,
        input_payload={
            "prompt": "delegate research",
            "handoff_to_agent_id": researcher_id,
            "handoff_reason": "needs researcher",
        },
    )

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 200

    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["status"] == "succeeded"
    handoff = body["output_payload"]["handoff"]
    assert handoff["status"] == HANDOFF_STATUS_DELEGATED
    assert handoff["target_agent_id"] == researcher_id
    assert handoff["target_agent_type"] == "researcher"
    assert handoff["child_run_enqueued"] is True
    assert handoff["child_run_id"]

    child = client.get(f"/agent-runs/{handoff['child_run_id']}", headers=auth_headers).json()
    assert child["status"] == "queued"
    assert child["agent_id"] == researcher_id
    assert child["metadata"]["parent_agent_run_id"] == run["id"]
    assert child["metadata"]["handoff_depth"] == 1

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    ).json()
    assert llm_requests == []

    rows = asyncio.run(store.list_for_run(UUID(run["id"])))
    node_names = {row.node_name for row in rows}
    assert "handoff_gate" in node_names
    assert "handoff_record" in node_names
    assert "llm_call" not in node_names


def test_graph_handoff_rejects_disallowed_target(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    researcher_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher",
    )
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orchestrator",
    )
    run = _create_run(
        client,
        auth_headers,
        researcher_id,
        input_payload={
            "prompt": "invalid delegate",
            "handoff_to_agent_id": orchestrator_id,
        },
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 500
    assert "handoff_not_allowed" in response.json()["detail"]

    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["status"] == "failed"
    assert body.get("error") == "handoff_not_allowed"


def test_graph_handoff_skipped_when_no_target(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Solo",
    )
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "no handoff"},
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["status"] == "succeeded"
    assert "handoff" not in body.get("output_payload", {})


@pytest.mark.asyncio
async def test_evaluate_graph_handoff_none(db_session) -> None:
    from app.db.models.user import UserTable
    from app.db.repositories.user_repo import UserRepository
    from app.schemas.crud import ProjectCreate
    from app.services.projects_service import ProjectService

    owner = await UserRepository(db_session).create(UserTable(telegram_id=9301))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Handoff Unit"),
    )
    decision = await evaluate_graph_handoff(
        db_session,
        owner_id=owner.id,
        project_id=project.id,
        source_agent_id=uuid4(),
        source_agent_type=AgentType.ORCHESTRATOR,
        request=None,
    )
    assert decision.status == HANDOFF_STATUS_NONE


def test_graph_handoff_execute_child_runs_target_agent(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAPH_HANDOFF_EXECUTE_CHILD", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orchestrator Exec",
    )
    researcher_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher Exec",
    )
    run = _create_run(
        client,
        auth_headers,
        orchestrator_id,
        input_payload={
            "prompt": "run child now",
            "handoff_to_agent_id": researcher_id,
            "handoff_execute_child": True,
        },
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200

    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    handoff = parent["output_payload"]["handoff"]
    assert handoff["child_run_executed"] is True
    assert handoff["child_run_status"] == "succeeded"

    child = client.get(f"/agent-runs/{handoff['child_run_id']}", headers=auth_headers).json()
    assert child["status"] == "succeeded"
    assert child["agent_id"] == researcher_id

    get_settings.cache_clear()


def test_child_run_blocks_nested_handoff_at_max_depth(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    researcher_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher Depth",
    )
    copywriter_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="copywriter",
        name="Copywriter Depth",
    )

    nested = _create_run(
        client,
        auth_headers,
        researcher_id,
        input_payload={
            "prompt": "nested handoff",
            "handoff_to_agent_id": copywriter_id,
        },
        metadata={"handoff_depth": 2},
    )
    response = client.post(
        f"/agent-runs/{nested['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 500
    assert "handoff_max_depth_exceeded" in response.json()["detail"]


def test_classic_executor_ignores_handoff_controls(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orchestrator Classic",
    )
    researcher_id = _create_agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher Classic",
    )
    run = _create_run(
        client,
        auth_headers,
        orchestrator_id,
        input_payload={
            "prompt": "classic",
            "handoff_to_agent_id": researcher_id,
        },
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert "handoff" not in body.get("output_payload", {})
