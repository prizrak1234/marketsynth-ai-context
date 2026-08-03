"""Phase 3.1 — graph state hardening and in-memory checkpoints."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.graphs.context import GraphRunContext
from app.graphs.contracts import (
    AgentGraphState,
    assert_no_graph_state_secrets,
    state_snapshot_for_checkpoint,
)
from app.graphs.node_runner import run_graph_node
from app.llm.contracts import LLMGenerateOutput
from app.schemas.contracts import AgentRunStatus, LLMProvider
from app.tools.contracts import ToolCall, ToolDefinition
from app.tools.registry import ToolRegistry
from fastapi.testclient import TestClient
from langchain_core.runnables import RunnableConfig


def _node_config(ctx: GraphRunContext) -> dict:
    return {"configurable": {"graph_run_context": ctx}}


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Graph CP Project"}, headers=headers)
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
    input_payload: dict | None = None,
) -> dict:
    response = client.post(
        "/agent-runs",
        json={
            "agent_id": agent_id,
            "input_payload": input_payload or {"prompt": "checkpoint test"},
            "metadata": {},
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _register_memory_search() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="memory.search",
            description="Search memory",
            parameters_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
            enabled=True,
        ),
    )
    return registry


def test_initial_graph_state_has_trace_metadata() -> None:
    owner_id = uuid4()
    state = AgentGraphState.create_initial(
        owner_id=owner_id,
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=uuid4(),
        input_payload={"prompt": "hello"},
        graph_version=get_settings().graph_version,
        trace_id="trace-test-1",
        max_steps=10,
    )
    assert state.graph_version == get_settings().graph_version
    assert state.trace_id == "trace-test-1"
    assert state.max_steps == 10
    assert state.step_count == 0
    assert state.completed_nodes == []
    assert state.started_at is not None


def test_state_rejects_secret_like_keys() -> None:
    state = AgentGraphState.create_initial(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=uuid4(),
        input_payload={"api_key": "sk-secret"},
        graph_version=get_settings().graph_version,
        trace_id="trace-secret",
        max_steps=5,
    )
    with pytest.raises(ValueError, match="forbidden"):
        assert_no_graph_state_secrets(state)


@pytest.mark.asyncio
async def test_node_runner_records_completed_node() -> None:
    from app.graphs.context import GraphRunContext

    store = InMemoryGraphCheckpointStore()
    ctx = GraphRunContext(
        session=AsyncMock(),
        owner_id=uuid4(),
        run_id=uuid4(),
        agent=object(),
        run=AsyncMock(),
        agent_runs=AsyncMock(),
        llm_requests=AsyncMock(),
        provider=LLMProvider.MOCK,
        model="mock-model",
        temperature=None,
        max_tokens=None,
        adapter=AsyncMock(),
        available_tools=[],
        tool_choice=None,
        permission_policy={},
        provider_tools=None,
        llm_metadata={},
        stored_input_payload={},
        prompt_metadata={},
        trace_id="trace-node-ok",
        max_steps=10,
        checkpoint_store=store,
    )

    async def ok_fn(state: dict, config: RunnableConfig) -> dict:
        return {"status": AgentRunStatus.RUNNING.value}

    base = AgentGraphState.create_initial(
        owner_id=ctx.owner_id,
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=ctx.run_id,
        input_payload={"prompt": "x"},
        graph_version=get_settings().graph_version,
        trace_id=ctx.trace_id,
        max_steps=10,
    ).to_graph_dict()

    result = await run_graph_node(
        "build_prompt",
        base,
        ok_fn,
        {"configurable": {"graph_run_context": ctx}},
    )
    assert "build_prompt" in result["completed_nodes"]
    assert result["step_count"] == 1
    assert result["current_node"] == "build_prompt"


@pytest.mark.asyncio
async def test_node_runner_records_failed_node_safely() -> None:
    from app.graphs.context import GraphRunContext

    ctx = GraphRunContext(
        session=AsyncMock(),
        owner_id=uuid4(),
        run_id=uuid4(),
        agent=object(),
        run=AsyncMock(),
        agent_runs=AsyncMock(),
        llm_requests=AsyncMock(),
        provider=LLMProvider.MOCK,
        model="mock-model",
        temperature=None,
        max_tokens=None,
        adapter=AsyncMock(),
        available_tools=[],
        tool_choice=None,
        permission_policy={},
        provider_tools=None,
        llm_metadata={},
        stored_input_payload={},
        prompt_metadata={},
        trace_id="trace-node-fail",
        checkpoints_enabled=False,
    )

    async def boom(_state: dict, _config: RunnableConfig) -> dict:
        raise RuntimeError("sk-super-secret-token")

    base = AgentGraphState.create_initial(
        owner_id=ctx.owner_id,
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=ctx.run_id,
        input_payload={"prompt": "x"},
        graph_version=get_settings().graph_version,
        trace_id=ctx.trace_id,
        max_steps=10,
    ).to_graph_dict()

    result = await run_graph_node(
        "llm_call",
        base,
        boom,
        {"configurable": {"graph_run_context": ctx}},
    )
    assert result["failed_node"] == "llm_call"
    assert result["status"] == AgentRunStatus.FAILED.value
    assert "sk-super-secret" not in json.dumps(result)


@pytest.mark.asyncio
async def test_node_runner_increments_step_count() -> None:
    from app.graphs.context import GraphRunContext

    ctx = GraphRunContext(
        session=AsyncMock(),
        owner_id=uuid4(),
        run_id=uuid4(),
        agent=object(),
        run=AsyncMock(),
        agent_runs=AsyncMock(),
        llm_requests=AsyncMock(),
        provider=LLMProvider.MOCK,
        model="mock-model",
        temperature=None,
        max_tokens=None,
        adapter=AsyncMock(),
        available_tools=[],
        tool_choice=None,
        permission_policy={},
        provider_tools=None,
        llm_metadata={},
        stored_input_payload={},
        prompt_metadata={},
        checkpoints_enabled=False,
    )

    async def ok(_state: dict, _config: RunnableConfig) -> dict:
        return {}

    base = AgentGraphState.create_initial(
        owner_id=ctx.owner_id,
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=ctx.run_id,
        input_payload={},
        graph_version=get_settings().graph_version,
        trace_id="trace-steps",
        max_steps=10,
    ).to_graph_dict()

    cfg = _node_config(ctx)
    first = await run_graph_node("build_prompt", base, ok, cfg)
    second = await run_graph_node("llm_call", first, ok, cfg)
    assert second["step_count"] == 2


@pytest.mark.asyncio
async def test_max_steps_exceeded_returns_safe_failure() -> None:
    from app.graphs.context import GraphRunContext

    ctx = GraphRunContext(
        session=AsyncMock(),
        owner_id=uuid4(),
        run_id=uuid4(),
        agent=object(),
        run=AsyncMock(),
        agent_runs=AsyncMock(),
        llm_requests=AsyncMock(),
        provider=LLMProvider.MOCK,
        model="mock-model",
        temperature=None,
        max_tokens=None,
        adapter=AsyncMock(),
        available_tools=[],
        tool_choice=None,
        permission_policy={},
        provider_tools=None,
        llm_metadata={},
        stored_input_payload={},
        prompt_metadata={},
        checkpoints_enabled=False,
        max_steps=1,
    )

    async def ok(_state: dict, _config: RunnableConfig) -> dict:
        return {}

    base = AgentGraphState.create_initial(
        owner_id=ctx.owner_id,
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=ctx.run_id,
        input_payload={},
        graph_version=get_settings().graph_version,
        trace_id="trace-max",
        max_steps=1,
    ).to_graph_dict()
    base["step_count"] = 1

    result = await run_graph_node("tool_execute", base, ok, _node_config(ctx))
    assert result["error"] == "graph_max_steps_exceeded"
    assert result["failed_node"] == "tool_execute"


@pytest.mark.asyncio
async def test_checkpoint_saved_after_successful_node() -> None:
    from app.graphs.context import GraphRunContext

    store = InMemoryGraphCheckpointStore()
    run_id = uuid4()
    ctx = GraphRunContext(
        session=AsyncMock(),
        owner_id=uuid4(),
        run_id=run_id,
        agent=object(),
        run=AsyncMock(),
        agent_runs=AsyncMock(),
        llm_requests=AsyncMock(),
        provider=LLMProvider.MOCK,
        model="mock-model",
        temperature=None,
        max_tokens=None,
        adapter=AsyncMock(),
        available_tools=[],
        tool_choice=None,
        permission_policy={},
        provider_tools=None,
        llm_metadata={},
        stored_input_payload={},
        prompt_metadata={},
        trace_id="trace-cp",
        checkpoint_store=store,
    )

    async def ok(_state: dict, _config: RunnableConfig) -> dict:
        return {"status": AgentRunStatus.RUNNING.value}

    base = AgentGraphState.create_initial(
        owner_id=ctx.owner_id,
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=run_id,
        input_payload={"prompt": "cp"},
        graph_version=get_settings().graph_version,
        trace_id=ctx.trace_id,
        max_steps=10,
    ).to_graph_dict()

    await run_graph_node("build_prompt", base, ok, {"configurable": {"graph_run_context": ctx}})
    rows = await store.list_for_run(run_id, trace_id=ctx.trace_id)
    assert len(rows) == 1
    assert rows[0].node_name == "build_prompt"


def test_checkpoint_snapshot_has_no_secrets() -> None:
    snapshot = state_snapshot_for_checkpoint(
        {
            "input_payload": {"prompt": "safe"},
            "messages": [],
            "trace_id": "t1",
            "graph_version": get_settings().graph_version,
        },
    )
    assert_no_graph_state_secrets(snapshot)
    with pytest.raises(ValueError):
        assert_no_graph_state_secrets(
            {
                **snapshot,
                "input_payload": {"token": "bearer abc"},
            },
        )


def _patch_runner_with_store(store: InMemoryGraphCheckpointStore):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, session, agent_run_service, llm_request_service, **kwargs):
            super().__init__(
                session,
                agent_run_service,
                llm_request_service,
                checkpoint_store=store,
            )

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def test_graph_dry_run_saves_checkpoints_for_nodes(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    store = InMemoryGraphCheckpointStore()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id, input_payload={"prompt": "cp nodes"})

    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 200
    rows = asyncio.run(store.list_for_run(UUID(run["id"])))
    node_names = [row.node_name for row in rows]
    assert "build_prompt" in node_names
    assert "llm_call" in node_names
    assert "final_response" in node_names


def test_graph_run_without_tools_succeeds_with_checkpoints(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    store = InMemoryGraphCheckpointStore()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "no tools checkpoint"},
    )

    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    rows = asyncio.run(store.list_for_run(UUID(run["id"])))
    assert rows[0].state_snapshot.get("trace_id")
    assert len(rows) >= 3


@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_run_with_tool_succeeds_with_checkpoints(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_memory_search()
    store = InMemoryGraphCheckpointStore()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )

    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 200
    rows = asyncio.run(store.list_for_run(UUID(run["id"])))
    node_names = [row.node_name for row in rows]
    assert "tool_prepare" in node_names
    assert "tool_execute" in node_names
    assert "llm_follow_up" in node_names


@patch("app.llm.mock_adapter.MockLLMAdapter.generate", new_callable=AsyncMock)
@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_nested_tool_calls_still_fail_with_checkpoints(
    mock_get_registry: AsyncMock,
    mock_generate: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_memory_search()
    mock_generate.side_effect = [
        LLMGenerateOutput(
            content="",
            provider=LLMProvider.MOCK,
            model="mock-model",
            tool_calls=[
                ToolCall(id="call_n", name="memory.search", arguments={"query": "x"}),
            ],
        ),
        LLMGenerateOutput(
            content="",
            provider=LLMProvider.MOCK,
            model="mock-model",
            tool_calls=[
                ToolCall(id="call_n2", name="memory.search", arguments={"query": "y"}),
            ],
        ),
    ]
    store = InMemoryGraphCheckpointStore()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )

    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 500
    assert "nested_tool_calls_not_supported" in response.json()["detail"]
    run_body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert run_body["status"] == "failed"
    assert run_body.get("error") == "nested_tool_calls_not_supported"
    rows = asyncio.run(store.list_for_run(UUID(run["id"])))
    checkpoint_nodes = {row.node_name for row in rows}
    assert "build_prompt" in checkpoint_nodes
    assert "llm_call" in checkpoint_nodes
    assert "tool_execute" in checkpoint_nodes


def test_classic_executor_unaffected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id, input_payload={"prompt": "classic"})

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["output_payload"].get("execution_engine") is None


def test_graph_max_steps_setting_respected(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAPH_MAX_STEPS", "2")
    get_settings.cache_clear()

    store = InMemoryGraphCheckpointStore()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 500
    rows = asyncio.run(store.list_for_run(UUID(run["id"])))
    assert "graph_max_steps_exceeded" in response.json()["detail"] or any(
        row.state_snapshot.get("error") == "graph_max_steps_exceeded" for row in rows
    )
