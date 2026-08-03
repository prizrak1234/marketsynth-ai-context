"""Phase 3.3 — graph memory load node."""

from __future__ import annotations

import asyncio
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.user_repo import UserRepository
from app.graphs.agent_graph import build_agent_graph
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.graphs.contracts import AgentGraphState, assert_no_graph_state_secrets
from app.graphs.memory_node import (
    load_graph_memory_context,
    resolve_memory_search_query,
)
from app.schemas.contracts import MemoryLayer
from app.schemas.crud import MemoryItemCreate, ProjectCreate
from app.services.memory_service import MemoryService
from app.services.projects_service import ProjectService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_resolve_memory_search_query_prefers_explicit_field() -> None:
    payload = {"memory_query": "  audience  ", "prompt": "x"}
    assert resolve_memory_search_query(payload) == "audience"


def test_agent_graph_includes_memory_load_node() -> None:
    nodes = set(build_agent_graph().nodes.keys())
    assert "memory_load" in nodes


def test_graph_state_memory_fields_pass_secret_scan() -> None:
    state = AgentGraphState(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=uuid4(),
        memory_load_status="loaded",
        memory_item_count=1,
        memory_query="audience",
        memory_context={
            "source": "graph_memory_load",
            "count": 1,
            "items": [{"content_preview": "safe preview"}],
        },
    )
    assert_no_graph_state_secrets(state)


@pytest.mark.asyncio
async def test_load_graph_memory_context_uses_input_when_provided(
    db_session: AsyncSession,
) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9201))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Graph Memory Input"),
    )
    result = await load_graph_memory_context(
        db_session,
        owner_id=owner.id,
        project_id=project.id,
        agent_id=uuid4(),
        input_payload={"prompt": "ignored"},
        provided_memory_context={"campaign": "spring"},
        skip_graph_memory_load=False,
    )
    assert result.status == "input_provided"
    assert result.memory_context == {"campaign": "spring"}


@pytest.mark.asyncio
async def test_load_graph_memory_context_searches_project_memory(
    db_session: AsyncSession,
) -> None:
    owner = await UserRepository(db_session).create(UserTable(telegram_id=9202))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Graph Memory Search"),
    )
    await MemoryService(db_session).create(
        MemoryItemCreate(
            user_id=owner.id,
            project_id=project.id,
            layer=MemoryLayer.L1_SESSION,
            key="note:audience",
            content="Target audience prefers short-form video",
            metadata={},
        ),
    )

    result = await load_graph_memory_context(
        db_session,
        owner_id=owner.id,
        project_id=project.id,
        agent_id=uuid4(),
        input_payload={"prompt": "short-form"},
        provided_memory_context=None,
        skip_graph_memory_load=False,
    )
    assert result.status == "loaded"
    assert result.item_count == 1
    assert isinstance(result.memory_context, dict)
    assert result.memory_context["count"] == 1


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Graph Memory E2E"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
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
) -> dict:
    response = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": input_payload, "metadata": {}},
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


def test_graph_dry_run_loads_memory_before_prompt(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    project = client.get(f"/projects/{project_id}", headers=auth_headers).json()
    owner_id = UUID(project["owner_id"])

    async def _seed_memory() -> None:
        await MemoryService(db_session).create(
            MemoryItemCreate(
                user_id=owner_id,
                project_id=UUID(project_id),
                layer=MemoryLayer.L1_SESSION,
                key="campaign",
                content="Graph memory load integration note",
                metadata={},
            ),
        )

    asyncio.run(_seed_memory())

    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "integration note"},
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
    assert body["output_payload"]["memory"]["memory_load_status"] == "loaded"
    assert body["output_payload"]["memory"]["memory_item_count"] >= 1

    rows = asyncio.run(store.list_for_run(UUID(run["id"])))
    assert any(row.node_name == "memory_load" for row in rows)
    memory_snapshot = next(row.state_snapshot for row in rows if row.node_name == "memory_load")
    assert memory_snapshot.get("memory_load_status") == "loaded"


def test_graph_skips_memory_load_when_disabled(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAPH_MEMORY_ENABLED", "false")
    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id, input_payload={"prompt": "hello"})

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["output_payload"]["memory"]["memory_load_status"] == "skipped"
    get_settings.cache_clear()


def test_classic_executor_unaffected_by_graph_memory_node(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id, input_payload={"prompt": "classic path"})

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert "memory" not in body.get("output_payload", {})
