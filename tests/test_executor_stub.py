"""Dry-run executor stub and hardening tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.db.models.agent import AgentTable
from app.db.models.agent_run import AgentRunTable
from app.db.models.project import ProjectTable
from app.db.models.user import UserTable
from app.db.repositories.agent_runs import AgentRunRepository
from app.schemas.contracts import AgentRunStatus, AgentStatus, AgentType
from app.tools.registry import ToolRegistry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _create_project(client: TestClient, headers: dict[str, str], name: str = "Exec Project") -> str:
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


def _create_task(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/tasks",
        json={"project_id": project_id, "title": "Executor task"},
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
        "input_payload": input_payload or {"prompt": "dry-run"},
        "metadata": {"source": "executor-test"},
    }
    if task_id is not None:
        payload["task_id"] = task_id
    response = client.post("/agent-runs", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_dry_run_succeeds_and_marks_agent_run_succeeded(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["output_payload"]["content"] == "Mock LLM response"
    assert "llm_request_id" in body["output_payload"]


def test_dry_run_creates_llm_request_and_response(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id, input_payload={"prompt": "hello"})

    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

    listed = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    )
    assert listed.status_code == 200
    requests = listed.json()
    assert len(requests) == 1
    assert requests[0]["provider"] == "mock"
    assert requests[0]["model"] == "mock-model"
    assert requests[0]["status"] == "succeeded"
    assert requests[0]["input_payload"]["input"] == {"prompt": "hello"}
    assert requests[0]["prompt_metadata"]["agent_type"] == "researcher"
    assert requests[0]["prompt_metadata"]["prompt_template_id"] == "default:researcher"
    from tests.researcher_tool_names import (
        RESEARCHER_READ_ONLY_TOOL_COUNT,
        RESEARCHER_READ_ONLY_TOOL_NAMES,
    )

    assert requests[0]["request_metadata"]["tools_metadata"] == {
        "tools_enabled": True,
        "tool_count": RESEARCHER_READ_ONLY_TOOL_COUNT,
        "tool_names": RESEARCHER_READ_ONLY_TOOL_NAMES,
        "tool_choice": None,
        "tool_calls_detected": 0,
        "tool_calls_executed": 0,
        "tool_calls_skipped": 0,
        "tool_results": [],
        "tool_executions": [],
        "permission_policy": {
            "agent_type": "researcher",
            "execution_mode": "no_op",
            "policy_execution_mode": "no_op",
            "allowed_tool_count": RESEARCHER_READ_ONLY_TOOL_COUNT,
        },
        "tools": {"executed_count": 0, "failed_count": 0, "tool_names": []},
    }

    detail = client.get(f"/llm-requests/{requests[0]['id']}", headers=auth_headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["response"] is not None
    assert payload["response"]["output_payload"]["content"] == "Mock LLM response"
    assert payload["request"]["id"] == requests[0]["id"]


def test_dry_run_preserves_task_agent_run_chain(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    task_id = _create_task(client, auth_headers, project_id)
    client.patch(f"/tasks/{task_id}", json={"agent_id": agent_id}, headers=auth_headers)
    run = _create_run(client, auth_headers, agent_id, task_id=task_id)

    client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

    llm_request = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    ).json()[0]
    assert llm_request["agent_id"] == agent_id
    assert llm_request["agent_run_id"] == run["id"]
    assert llm_request["task_id"] == task_id
    assert llm_request["project_id"] == project_id


def test_cannot_execute_run_not_in_queued(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)
    assert client.post(f"/agent-runs/{run['id']}/running", headers=auth_headers).status_code == 200

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 409


def test_execute_claims_only_queued_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)
    assert client.post(f"/agent-runs/{run['id']}/running", headers=auth_headers).status_code == 200

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 409

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    ).json()
    assert llm_requests == []


def test_double_execute_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    first = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert first.status_code == 200
    assert first.json()["status"] == "succeeded"

    second = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert second.status_code == 409

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    ).json()
    assert len(llm_requests) == 1


def test_execute_running_run_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)
    assert client.post(f"/agent-runs/{run['id']}/running", headers=auth_headers).status_code == 200

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 409


def test_execute_succeeded_run_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)
    first_execute = client.post(
        f"/agent-runs/{run['id']}/execute-dry-run",
        headers=auth_headers,
    )
    assert first_execute.status_code == 200

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 409


def test_execute_failed_run_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)
    assert (
        client.post(
            f"/agent-runs/{run['id']}/failed",
            json={"error": "manual fail"},
            headers=auth_headers,
        ).status_code
        == 200
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_claim_queued_run_atomic(db_session: AsyncSession) -> None:
    user = UserTable(telegram_id=424242)
    db_session.add(user)
    await db_session.flush()

    project = ProjectTable(owner_id=user.id, name="Claim Project")
    db_session.add(project)
    await db_session.flush()

    agent = AgentTable(
        project_id=project.id,
        owner_id=user.id,
        type=AgentType.RESEARCHER,
        name="Claim Agent",
        status=AgentStatus.ACTIVE,
    )
    db_session.add(agent)
    await db_session.flush()

    run = AgentRunTable(
        owner_id=user.id,
        project_id=project.id,
        agent_id=agent.id,
        status=AgentRunStatus.QUEUED,
        input_payload={"prompt": "claim"},
    )
    db_session.add(run)
    await db_session.flush()

    repo = AgentRunRepository(db_session)
    claimed = await repo.claim_queued_run(run.id, user.id)
    assert claimed is not None
    assert claimed.status == AgentRunStatus.RUNNING
    assert claimed.started_at is not None

    second_claim = await repo.claim_queued_run(run.id, user.id)
    assert second_claim is None


def test_foreign_owner_cannot_execute_dry_run(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    response = client.post(
        f"/agent-runs/{run['id']}/execute-dry-run",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_archived_agent_blocks_dry_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)
    assert client.delete(f"/agents/{agent_id}", headers=auth_headers).status_code == 200

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 409
    assert "archived" in response.json()["detail"].lower()

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    ).json()
    assert llm_requests == []


def test_executor_failure_marks_request_and_run_failed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    with patch(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        new=AsyncMock(side_effect=RuntimeError("mock provider down")),
    ):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 500

    failed_run = client.get(f"/agent-runs/{run['id']}", headers=auth_headers)
    assert failed_run.status_code == 200
    assert failed_run.json()["status"] == "failed"
    assert "mock provider down" in failed_run.json()["error"]

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    ).json()
    assert len(llm_requests) == 1
    assert llm_requests[0]["status"] == "failed"


def test_executor_does_not_leave_run_running_after_exception(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    with patch(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)

    final_run = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert final_run["status"] == "failed"
    assert final_run["status"] != "running"


def test_execute_nonexistent_run_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        f"/agent-runs/{uuid4()}/execute-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 404


def _register_test_tool(name: str = "search_brief") -> ToolRegistry:
    from app.tools.contracts import ToolDefinition

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


@patch("app.executors.agent_run_executor.get_tool_registry")
def test_dry_run_detects_mock_tool_call_and_skips_execution(
    mock_get_registry: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_get_registry.return_value = _register_test_tool()
    project_id = _create_project(client, auth_headers, name="Tool Call Project")
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(
        client,
        auth_headers,
        agent_id,
        input_payload={
            "prompt": "find audience insights",
            "mock_tool_call": {
                "id": "call_test_1",
                "type": "function",
                "function": {
                    "name": "search_brief",
                    "arguments": {"query": "audience"},
                },
            },
        },
    )

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert (
        response.json()["output_payload"]["content"]
        == "Mock researcher final answer after tools"
    )
    assert response.json()["output_payload"]["follow_up_llm_call"] is True

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run["id"]},
        headers=auth_headers,
    ).json()
    assert len(llm_requests) == 2
    initial = next(
        item
        for item in llm_requests
        if item["request_metadata"].get("phase") != "tool_follow_up"
    )
    tools_metadata = initial["request_metadata"]["tools_metadata"]
    assert tools_metadata["tool_calls_detected"] == 1
    assert tools_metadata["tool_calls_executed"] == 0
    assert tools_metadata["tool_calls_skipped"] == 1
    assert tools_metadata["tool_results"][0]["reason"] == "tool_execution_disabled"
    assert tools_metadata["permission_policy"]["execution_mode"] == "no_op"
    assert tools_metadata["tool_rounds"] == 1
    assert tools_metadata["follow_up_llm_call"] is True

    detail = client.get(f"/llm-requests/{initial['id']}", headers=auth_headers).json()
    assert detail["response"]["raw_response"] == {}
    assert "tool_calls" not in detail["response"]["output_payload"]


@patch("app.llm.mock_adapter.MockLLMAdapter.generate", new_callable=AsyncMock)
@patch("app.executors.agent_run_executor.get_tool_registry")
def test_dry_run_makes_follow_up_llm_call_when_tool_calls_present(
    mock_get_registry: AsyncMock,
    mock_generate: AsyncMock,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from app.llm.contracts import LLMGenerateOutput
    from app.schemas.contracts import LLMProvider
    from app.tools.contracts import ToolCall

    mock_get_registry.return_value = _register_test_tool()
    mock_generate.side_effect = [
        LLMGenerateOutput(
            content="",
            provider=LLMProvider.MOCK,
            model="mock-model",
            tool_calls=[ToolCall(id="call_1", name="search_brief", arguments={"query": "x"})],
        ),
        LLMGenerateOutput(
            content="Mock LLM response",
            provider=LLMProvider.MOCK,
            model="mock-model",
        ),
    ]

    project_id = _create_project(client, auth_headers, name="Follow-up LLM Call Project")
    agent_id = _create_agent(client, auth_headers, project_id)
    run = _create_run(client, auth_headers, agent_id)

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert mock_generate.await_count == 2
