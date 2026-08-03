"""Phase 3.2 — graph tool node layer and routing."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.graphs.agent_graph import build_agent_graph
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.graphs.contracts import AgentGraphState, assert_no_graph_state_secrets
from app.graphs.routing import (
    route_after_llm_call,
    route_after_tool_finalize,
    route_after_tool_prepare,
)
from app.graphs.tool_node import execute_graph_tool_round, plan_graph_tool_round
from app.schemas.contracts import AgentRunStatus, LLMProvider
from app.tools.contracts import ToolCall, ToolDefinition, ToolResult
from app.tools.registry import ToolRegistry
from fastapi.testclient import TestClient


def _register_search_brief() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="search_brief",
            description="No-op stub",
            parameters_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "additionalProperties": False,
            },
            enabled=True,
        ),
    )
    return registry


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


def test_plan_graph_tool_round_splits_excess_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_TOOL_CALLS_PER_ROUND", "1")
    get_settings.cache_clear()
    calls = [
        ToolCall(id="a", name="search_brief", arguments={"query": "one"}),
        ToolCall(id="b", name="search_brief", arguments={"query": "two"}),
    ]
    plan = plan_graph_tool_round(calls)
    assert len(plan.accepted_calls) == 1
    assert len(plan.skipped_calls) == 1
    get_settings.cache_clear()


def test_routing_skips_tool_path_without_tool_calls() -> None:
    state = {"has_tool_calls": False, "status": AgentRunStatus.RUNNING.value}
    assert route_after_llm_call(state) == "final_response"


def test_routing_tool_prepare_to_execute_when_planned() -> None:
    state = {"tool_calls_planned": 2, "status": AgentRunStatus.RUNNING.value}
    assert route_after_tool_prepare(state) == "tool_execute"


def test_routing_tool_finalize_to_follow_up() -> None:
    state = {"follow_up_llm_call": True, "status": AgentRunStatus.RUNNING.value}
    assert route_after_tool_finalize(state) == "llm_follow_up"


def test_graph_state_tool_fields_pass_secret_scan() -> None:
    state = AgentGraphState(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=uuid4(),
        pending_tool_calls=[
            {"id": "c1", "name": "memory.search", "arguments": {"query": "safe"}},
        ],
        tool_calls_planned=1,
        tool_calls_executed=1,
        tool_round_status="executed",
    )
    assert_no_graph_state_secrets(state)


def test_agent_graph_has_tool_subnodes() -> None:
    graph = build_agent_graph()
    node_names = set(graph.nodes.keys())
    assert {"tool_prepare", "tool_execute", "tool_finalize", "llm_follow_up"}.issubset(node_names)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Graph Tool Project"}, headers=headers)
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


@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_multi_tool_round_succeeds(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_search_brief()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={
            "prompt": "multi",
            "mock_tool_call": [
                {
                    "id": "call_a",
                    "type": "function",
                    "function": {"name": "search_brief", "arguments": {"query": "a"}},
                },
                {
                    "id": "call_b",
                    "type": "function",
                    "function": {"name": "search_brief", "arguments": {"query": "b"}},
                },
            ],
        },
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["status"] == "succeeded"
    tools = body["output_payload"].get("tools", {})
    assert tools.get("tool_names") == ["search_brief"]
    assert body["output_payload"]["tool_audit"]["logged_count"] == 2

    logs = client.get(
        f"/agent-runs/{run['id']}/tool-executions",
        headers=auth_headers,
    ).json()
    assert [log["tool_call_id"] for log in logs] == ["call_a", "call_b"]


@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_tool_limit_exceeded_in_round(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_TOOL_CALLS_PER_ROUND", "1")
    get_settings.cache_clear()
    mock_get_registry.return_value = _register_search_brief()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={
            "prompt": "limit",
            "mock_tool_call": [
                {
                    "id": "call_a",
                    "type": "function",
                    "function": {"name": "search_brief", "arguments": {"query": "a"}},
                },
                {
                    "id": "call_b",
                    "type": "function",
                    "function": {"name": "search_brief", "arguments": {"query": "b"}},
                },
            ],
        },
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["status"] == "succeeded"
    tools = body["output_payload"].get("tools", {})
    assert tools.get("failed_count") == 1
    assert tools.get("tool_names") == ["search_brief"]
    assert body["output_payload"]["tool_audit"]["logged_count"] == 1
    get_settings.cache_clear()


@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_run_records_tool_round_in_checkpoints(
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
    by_node = {row.node_name: row.state_snapshot for row in rows}
    assert by_node["tool_prepare"].get("tool_round_status") == "planned"
    assert by_node["tool_execute"].get("tool_round_status") == "executed"
    assert by_node["tool_finalize"].get("tool_round_status") == "complete"


@pytest.mark.asyncio
async def test_execute_graph_tool_round_unit() -> None:
    from unittest.mock import MagicMock

    from app.graphs.context import GraphRunContext

    owner_id = uuid4()
    run_id = uuid4()
    llm_request_id = uuid4()
    agent = MagicMock()
    agent.id = uuid4()
    agent.type = "researcher"
    run = MagicMock()
    run.project_id = uuid4()
    run.task_id = None

    ctx = GraphRunContext(
        session=AsyncMock(),
        owner_id=owner_id,
        run_id=run_id,
        agent=agent,
        run=run,
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
        audit_tracker=None,
    )

    plan = plan_graph_tool_round(
        [ToolCall(id="c1", name="search_brief", arguments={"query": "x"})],
        max_per_round=5,
    )

    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(
        return_value=ToolResult(
            call_id="c1",
            name="search_brief",
            status="succeeded",
            output={"ok": True},
        ),
    )

    registry = _register_search_brief()
    result = await execute_graph_tool_round(
        session=ctx.session,
        ctx=ctx,
        owner_id=owner_id,
        llm_request_id=llm_request_id,
        plan=plan,
        available_tools=list(registry.list_for_agent(agent.type)),
        tool_choice=None,
        permission_policy={},
        executor=mock_executor,
    )

    assert result.accepted_count == 1
    assert len(result.tool_results) == 1
    assert result.tools_metadata["tool_rounds"] == 1
