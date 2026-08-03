"""Phase 2.22 — multiple tool calls in a single tool round."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from app.tools.contracts import ToolDefinition
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


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Multi Tool Project"}, headers=headers)
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


def _create_run(client: TestClient, headers: dict[str, str], agent_id: str, **payload) -> dict:
    response = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": payload, "metadata": {}},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_two_tool_calls_execute_in_order_with_audit(
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
        prompt="multi",
        mock_tool_call=[
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
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["tools"] == {
        "executed_count": 0,
        "failed_count": 0,
        "tool_names": ["search_brief"],
    }
    assert body["output_payload"]["tool_audit"]["logged_count"] == 2

    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    assert [log["tool_call_id"] for log in logs] == ["call_a", "call_b"]


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_one_failed_tool_does_not_block_the_other(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
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
    mock_get_registry.return_value = registry

    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        prompt="mixed",
        mock_tool_call=[
            {
                "id": "call_bad",
                "type": "function",
                "function": {"name": "memory.search", "arguments": {"query": "   "}},
            },
            {
                "id": "call_ok",
                "type": "function",
                "function": {"name": "search_brief", "arguments": {"query": "ok"}},
            },
        ],
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["tools"]["failed_count"] == 1
    assert body["output_payload"]["tools"]["tool_names"] == ["memory.search", "search_brief"]

    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    assert len(logs) == 2
    assert logs[0]["status"] == "failed"
    assert logs[1]["status"] == "skipped"


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_tool_call_limit_marks_excess_calls_failed(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_get_registry.return_value = _register_search_brief()
    monkeypatch.setenv("MAX_TOOL_CALLS_PER_ROUND", "2")
    from app.core.config import get_settings

    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        prompt="limit",
        mock_tool_call=[
            {
                "id": f"call_{index}",
                "type": "function",
                "function": {"name": "search_brief", "arguments": {"query": str(index)}},
            }
            for index in range(3)
        ],
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["output_payload"]["tools"]["failed_count"] == 1
    assert body["output_payload"]["tool_audit"]["logged_count"] == 2

    logs = client.get(f"/agent-runs/{run['id']}/tool-executions", headers=auth_headers).json()
    assert len(logs) == 2
    assert "tool_call_limit_exceeded" not in json.dumps(logs)
