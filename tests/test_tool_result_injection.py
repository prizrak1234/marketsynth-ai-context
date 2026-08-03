"""Phase 2.13 — tool result injection and follow-up LLM call tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from app.llm.contracts import LLMGenerateOutput
from app.llm.message_serialization import llm_message_to_provider_dict
from app.schemas.contracts import LLMProvider
from app.tools.contracts import ToolCall, ToolDefinition, ToolResult
from app.tools.registry import ToolRegistry
from app.tools.result_messages import (
    MAX_TOOL_RESULT_CONTENT_BYTES,
    build_tool_result_message,
    truncate_tool_result_content,
)
from fastapi.testclient import TestClient


def _create_project(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Injection Project",
) -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
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
            "input_payload": input_payload or {"prompt": "dry-run"},
            "metadata": {"source": "tool-injection-test"},
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _register_test_tool(name: str = "search_brief") -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name=name,
            description="Test tool",
            parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
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


def _initial_llm_request(requests: list[dict]) -> dict:
    return next(
        item for item in requests if item["request_metadata"].get("phase") != "tool_follow_up"
    )


def _follow_up_llm_request(requests: list[dict]) -> dict:
    return next(
        item for item in requests if item["request_metadata"].get("phase") == "tool_follow_up"
    )


def test_no_tool_calls_keeps_single_llm_request(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id, input_payload={"prompt": "plain answer"})

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["content"] == "Mock LLM response"
    assert body["output_payload"].get("follow_up_llm_call") is None

    requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    ).json()
    assert len(requests) == 1


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_force_tool_call_memory_search_runs_follow_up_llm(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_test_tool("memory.search")
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "find notes", "force_tool_call": "memory.search"},
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["content"] == "Mock researcher final answer after tools"
    assert body["output_payload"]["follow_up_llm_call"] is True
    assert body["output_payload"]["tool_rounds"] == 1

    requests = _llm_requests_for_run(client, run["id"], auth_headers)
    assert len(requests) == 2

    initial = _initial_llm_request(requests)
    follow_up = _follow_up_llm_request(requests)

    assert initial["status"] == "succeeded"
    assert follow_up["status"] == "succeeded"
    assert follow_up["request_metadata"]["parent_request_id"] == initial["id"]
    tools_metadata = follow_up["request_metadata"]["tools_metadata"]
    assert tools_metadata["tool_rounds"] == 1
    assert tools_metadata["follow_up_llm_call"] is True
    assert tools_metadata["nested_tool_calls"] is False


def test_tool_result_message_has_tool_role_and_call_id() -> None:
    from app.tools.result_builder import build_tool_success

    tool_call = ToolCall(id="call_test_1", name="memory.search", arguments={"query": "x"})
    result = ToolResult(
        call_id="call_test_1",
        name="memory.search",
        status="succeeded",
        output=build_tool_success("memory.search", {"count": 0, "items": []}),
    )
    message = build_tool_result_message(tool_call, result)
    provider_dict = llm_message_to_provider_dict(message)

    assert message.role == "tool"
    assert message.tool_call_id == "call_test_1"
    assert message.name == "memory.search"
    assert provider_dict["role"] == "tool"
    assert provider_dict["tool_call_id"] == "call_test_1"
    payload = json.loads(message.content or "")
    assert payload["ok"] is True
    assert payload["tool"] == "memory.search"


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_write_tool_call_is_skipped_in_follow_up_messages(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_test_tool("memory.write")
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={
            "prompt": "write memory",
            "mock_tool_call": {
                "id": "call_write_1",
                "type": "function",
                "function": {
                    "name": "memory.write",
                    "arguments": {"content": "secret"},
                },
            },
        },
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"

    requests = _llm_requests_for_run(client, run["id"], auth_headers)
    initial = _initial_llm_request(requests)
    tools_metadata = initial["request_metadata"]["tools_metadata"]
    assert tools_metadata["tool_calls_skipped"] == 1
    assert tools_metadata["tool_executions"][0]["reason"] == "tool_not_allowed"


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_bad_memory_search_args_produce_failed_tool_result(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_test_tool("memory.search")
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={
            "prompt": "search",
            "mock_tool_call": {
                "id": "call_bad_1",
                "type": "function",
                "function": {
                    "name": "memory.search",
                    "arguments": {"query": "   "},
                },
            },
        },
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"

    requests = _llm_requests_for_run(client, run["id"], auth_headers)
    initial = _initial_llm_request(requests)
    execution = initial["request_metadata"]["tools_metadata"]["tool_executions"][0]
    assert execution["status"] == "failed"
    assert execution["reason"] == "invalid_tool_arguments"


@patch("app.llm.mock_adapter.MockLLMAdapter.generate", new_callable=AsyncMock)
@patch("app.executors.agent_run_executor.get_tool_registry")
def test_nested_tool_calls_fail_run(
    mock_get_registry: AsyncMock,
    mock_generate: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from app.tools.contracts import ToolCall as ParsedToolCall

    mock_get_registry.return_value = _register_test_tool("search_brief")
    mock_generate.side_effect = [
        LLMGenerateOutput(
            content="",
            provider=LLMProvider.MOCK,
            model="mock-model",
            tool_calls=[ParsedToolCall(id="call_1", name="search_brief", arguments={"query": "x"})],
            finish_reason="tool_calls",
        ),
        LLMGenerateOutput(
            content="",
            provider=LLMProvider.MOCK,
            model="mock-model",
            tool_calls=[ParsedToolCall(id="call_2", name="search_brief", arguments={"query": "y"})],
            finish_reason="tool_calls",
        ),
    ]

    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 500

    final_run = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert final_run["status"] == "failed"
    assert "nested_tool_calls_not_supported" in final_run["error"]

    requests = _llm_requests_for_run(client, run["id"], auth_headers)
    follow_up = _follow_up_llm_request(requests)
    assert follow_up["status"] == "failed"
    assert follow_up["request_metadata"]["tools_metadata"]["nested_tool_calls"] is True


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_metadata_does_not_store_full_memory_content(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from app.tools.registry import MEMORY_SEARCH_TOOL, ToolRegistry

    registry = ToolRegistry()
    registry.register(MEMORY_SEARCH_TOOL)
    mock_get_registry.return_value = registry

    secret = "TOP_SECRET_MEMORY_CONTENT_SHOULD_NOT_APPEAR_IN_METADATA"
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    client.post(
        "/memory",
        json={
            "project_id": project_id,
            "layer": "l1_session",
            "key": "session:secret",
            "content": secret,
            "metadata": {"source": "test"},
        },
        headers=auth_headers,
    )

    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )
    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

    requests = _llm_requests_for_run(client, run["id"], auth_headers)
    serialized = json.dumps(requests)
    assert secret not in serialized


@patch("app.llm.mock_adapter.MockLLMAdapter.generate", new_callable=AsyncMock)
@patch("app.executors.agent_run_executor.get_tool_registry")
def test_tool_round_makes_two_llm_calls(
    mock_get_registry: AsyncMock,
    mock_generate: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from app.tools.contracts import ToolCall as ParsedToolCall

    mock_get_registry.return_value = _register_test_tool("search_brief")
    mock_generate.side_effect = [
        LLMGenerateOutput(
            content="",
            provider=LLMProvider.MOCK,
            model="mock-model",
            tool_calls=[ParsedToolCall(id="call_1", name="search_brief", arguments={"query": "x"})],
        ),
        LLMGenerateOutput(
            content="Final synthesized answer",
            provider=LLMProvider.MOCK,
            model="mock-model",
        ),
    ]

    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert mock_generate.await_count == 2
    assert response.json()["output_payload"]["content"] == "Final synthesized answer"


def test_tool_result_content_truncation() -> None:
    oversized = "x" * (MAX_TOOL_RESULT_CONTENT_BYTES + 100)
    truncated = truncate_tool_result_content(oversized)
    assert len(truncated.encode("utf-8")) <= MAX_TOOL_RESULT_CONTENT_BYTES
    assert truncated.endswith("...[truncated]")


def test_follow_up_generate_receives_tool_messages(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    patch_target = "app.llm.mock_adapter.MockLLMAdapter.generate"
    with patch(patch_target, new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = [
            LLMGenerateOutput(
                content="",
                provider=LLMProvider.MOCK,
                model="mock-model",
                tool_calls=[
                    ToolCall(
                        id="call_force_mock",
                        name="memory.search",
                        arguments={"query": "mock"},
                    ),
                ],
                finish_reason="tool_calls",
            ),
            LLMGenerateOutput(
                content="Mock LLM final answer after tools",
                provider=LLMProvider.MOCK,
                model="mock-model",
                finish_reason="stop",
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
        client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

        second_call_messages = mock_generate.await_args_list[1].args[0].messages
        tool_messages = [message for message in second_call_messages if message.role == "tool"]
        assert len(tool_messages) == 1
        assert tool_messages[0].tool_call_id == "call_force_mock"
        assert tool_messages[0].name == "memory.search"


@patch("app.executors.agent_run_executor.SafeNoOpToolExecutor.execute", new_callable=AsyncMock)
def test_request_id_is_passed_to_tool_execution_context(
    mock_execute: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from app.tools.contracts import ToolResult

    mock_execute.return_value = ToolResult(
        call_id="call_force_mock",
        name="memory.search",
        status="skipped",
        output={"reason": "tool_execution_disabled"},
    )

    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={"prompt": "search", "force_tool_call": "memory.search"},
    )
    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

    context = mock_execute.await_args.args[1]
    initial = _initial_llm_request(_llm_requests_for_run(client, run["id"], auth_headers))
    assert str(context.request_id) == initial["id"]
