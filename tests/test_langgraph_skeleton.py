"""Phase 3.0 — LangGraph orchestration skeleton tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.graphs import (
    AgentGraphState,
    assert_agent_graph_state_has_no_secrets,
    build_agent_graph,
    get_compiled_agent_graph,
    is_langgraph_execution_engine,
)
from app.graphs.contracts import GRAPH_CONTEXT_CONFIG_KEY
from app.llm.contracts import LLMGenerateOutput
from app.schemas.contracts import LLMProvider
from app.tools.contracts import ToolCall, ToolDefinition
from app.tools.registry import ToolRegistry
from fastapi.testclient import TestClient


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "LangGraph Project"}, headers=headers)
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
            "input_payload": input_payload or {"prompt": "graph dry-run"},
            "metadata": {"source": "langgraph-test"},
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


def _llm_requests_for_run(client: TestClient, run_id: str, headers: dict[str, str]) -> list[dict]:
    return client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=headers,
    ).json()


def test_graph_package_imports() -> None:
    graph = build_agent_graph()
    assert graph is not None
    compiled = get_compiled_agent_graph()
    assert compiled is not None
    assert GRAPH_CONTEXT_CONFIG_KEY == "graph_run_context"


def test_graph_state_rejects_secrets() -> None:
    state = AgentGraphState(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=uuid4(),
        input_payload={"prompt": "hello", "api_key": "sk-secret"},
    )
    with pytest.raises(ValueError, match="forbidden"):
        assert_agent_graph_state_has_no_secrets(state)

    safe_state = AgentGraphState(
        owner_id=uuid4(),
        project_id=uuid4(),
        agent_id=uuid4(),
        agent_run_id=uuid4(),
        input_payload={"prompt": "hello"},
    )
    assert_agent_graph_state_has_no_secrets(safe_state)


def test_default_execution_engine_is_classic() -> None:
    assert is_langgraph_execution_engine() is False


def test_graph_dry_run_without_tools_succeeds(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "plain graph answer"},
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["content"] == "Mock LLM response"
    assert body["output_payload"]["execution_engine"] == "langgraph"
    assert len(_llm_requests_for_run(client, run["id"], auth_headers)) == 1


@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_dry_run_with_one_tool_succeeds(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_memory_search()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    client.post(
        "/memory",
        json={
            "project_id": project_id,
            "layer": "l1_session",
            "key": "graph:1",
            "content": "graph memory note",
            "metadata": {},
        },
        headers=auth_headers,
    )
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["content"] == "Mock researcher final answer after tools"
    assert body["output_payload"]["follow_up_llm_call"] is True
    assert body["output_payload"]["tools"]["executed_count"] == 1


@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_injects_tool_envelope_into_follow_up_llm(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_memory_search()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )

    with patch(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.side_effect = [
            LLMGenerateOutput(
                content="",
                provider=LLMProvider.MOCK,
                model="mock-model",
                tool_calls=[
                    ToolCall(
                        id="call_graph_env",
                        name="memory.search",
                        arguments={"query": "graph"},
                    ),
                ],
            ),
            LLMGenerateOutput(
                content="Mock LLM final answer after tools",
                provider=LLMProvider.MOCK,
                model="mock-model",
            ),
        ]
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert mock_generate.await_count == 2
    follow_up_messages = mock_generate.await_args_list[1].args[0].messages
    tool_messages = [message for message in follow_up_messages if message.role == "tool"]
    assert len(tool_messages) == 1
    payload = json.loads(tool_messages[0].content or "")
    assert payload["ok"] is True
    assert payload["tool"] == "memory.search"


@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_writes_llm_request_and_response(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_memory_search()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200

    requests = _llm_requests_for_run(client, run["id"], auth_headers)
    assert len(requests) == 2
    assert all(item["status"] == "succeeded" for item in requests)
    assert requests[0]["request_metadata"]["executor"] == "langgraph-dry-run"


@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_writes_tool_audit_log(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_memory_search()
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    client.post(
        "/memory",
        json={
            "project_id": project_id,
            "layer": "l1_session",
            "key": "graph:audit",
            "content": "audit graph note",
            "metadata": {},
        },
        headers=auth_headers,
    )
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200

    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "memory.search"
    assert logs[0]["status"] == "succeeded"
    assert "audit graph note" not in json.dumps(logs)


@patch("app.llm.mock_adapter.MockLLMAdapter.generate", new_callable=AsyncMock)
@patch("app.graphs.tool_node.get_tool_registry")
def test_graph_rejects_nested_tool_calls(
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
                ToolCall(id="call_nested", name="memory.search", arguments={"query": "x"}),
            ],
        ),
        LLMGenerateOutput(
            content="",
            provider=LLMProvider.MOCK,
            model="mock-model",
            tool_calls=[
                ToolCall(id="call_nested_2", name="memory.search", arguments={"query": "y"}),
            ],
        ),
    ]

    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 500
    assert "nested_tool_calls_not_supported" in response.json()["detail"]

    run_body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert run_body["status"] == "failed"


def test_graph_preserves_agent_run_status_transitions(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    created = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert created["status"] == "queued"

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    finished = response.json()
    assert finished["status"] == "succeeded"
    assert finished["started_at"] is not None
    assert finished["finished_at"] is not None


def test_classic_executor_endpoint_still_default(
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
    assert body["output_payload"].get("execution_engine") is None
