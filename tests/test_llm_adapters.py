"""LLM adapter layer tests — mock/monkeypatch only, no network calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from app.core.exceptions import ExecutorError
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.litellm_adapter import LiteLLMAdapter
from app.llm.mock_adapter import MOCK_CONTENT, MOCK_MODEL, MockLLMAdapter, build_messages
from app.llm.registry import get_llm_adapter
from app.schemas.contracts import LLMProvider
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_mock_adapter_returns_stable_response() -> None:
    adapter = MockLLMAdapter()
    output = await adapter.generate(
        LLMGenerateInput(
            provider=LLMProvider.MOCK,
            model=MOCK_MODEL,
            messages=[LLMMessage(role="user", content="hello")],
        ),
    )
    assert output.content == MOCK_CONTENT
    assert output.provider == LLMProvider.MOCK
    assert output.model == MOCK_MODEL
    assert output.usage["total_tokens"] == 0


def test_registry_returns_mock_adapter() -> None:
    adapter = get_llm_adapter(LLMProvider.MOCK)
    assert isinstance(adapter, MockLLMAdapter)


def test_registry_returns_litellm_adapter_for_openai() -> None:
    adapter = get_llm_adapter(LLMProvider.OPENAI)
    assert isinstance(adapter, LiteLLMAdapter)


def test_unsupported_provider_raises_executor_error() -> None:
    with pytest.raises(ExecutorError, match="Unsupported LLM provider"):
        get_llm_adapter(LLMProvider.ANTHROPIC)


@pytest.mark.asyncio
async def test_build_messages_from_prompt() -> None:
    messages = build_messages({"prompt": "test prompt"})
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[-1].role == "user"
    assert messages[-1].content == "test prompt"


def test_executor_uses_adapter_layer(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Adapter Project"}, headers=auth_headers)
    assert project.status_code == 201
    project_id = project.json()["id"]

    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    )
    assert agent.status_code == 201
    agent_id = agent.json()["id"]

    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "via adapter"}},
        headers=auth_headers,
    )
    assert run.status_code == 201
    run_id = run.json()["id"]

    with patch(
        "app.executors.agent_run_executor.get_llm_adapter",
        wraps=get_llm_adapter,
    ) as registry_mock:
        response = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)

    assert response.status_code == 200
    registry_mock.assert_called_once_with(LLMProvider.MOCK)
    assert response.json()["output_payload"]["content"] == MOCK_CONTENT


def test_agent_config_llm_provider_model_in_llm_request(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Config Project"}, headers=auth_headers)
    project_id = project.json()["id"]

    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    )
    agent_id = agent.json()["id"]

    updated = client.patch(
        f"/agents/{agent_id}",
        json={
            "config": {
                "llm": {
                    "provider": "mock",
                    "model": "custom-mock-model",
                    "temperature": 0.2,
                    "max_tokens": 1000,
                },
            },
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200

    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "config test"}},
        headers=auth_headers,
    )
    run_id = run.json()["id"]
    execute = client.post(
        f"/agent-runs/{run_id}/execute-dry-run",
        headers=auth_headers,
    )
    assert execute.status_code == 200

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()
    assert len(llm_requests) == 1
    assert llm_requests[0]["provider"] == "mock"
    assert llm_requests[0]["model"] == "custom-mock-model"
    assert llm_requests[0]["input_payload"]["input"] == {"prompt": "config test"}
    assert llm_requests[0]["request_metadata"]["model"] == "custom-mock-model"
    assert llm_requests[0]["request_metadata"]["provider"] == "mock"
    assert llm_requests[0]["request_metadata"]["prompt_template_id"] == "default:researcher"


def test_adapter_failure_marks_request_and_run_failed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Fail Project"}, headers=auth_headers)
    project_id = project.json()["id"]
    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    )
    agent_id = agent.json()["id"]
    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "fail"}},
        headers=auth_headers,
    )
    run_id = run.json()["id"]

    with patch(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        new=AsyncMock(side_effect=RuntimeError("adapter exploded")),
    ):
        response = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)

    assert response.status_code == 500
    failed_run = client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()
    assert failed_run["status"] == "failed"
    assert "adapter exploded" in failed_run["error"]

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()
    assert len(llm_requests) == 1
    assert llm_requests[0]["status"] == "failed"


def test_unsupported_provider_in_agent_config_fails_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Unsupported Project"}, headers=auth_headers)
    project_id = project.json()["id"]
    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    )
    agent_id = agent.json()["id"]
    client.patch(
        f"/agents/{agent_id}",
        json={"config": {"llm": {"provider": "anthropic", "model": "claude-3"}}},
        headers=auth_headers,
    )

    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "nope"}},
        headers=auth_headers,
    )
    run_id = run.json()["id"]

    response = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 500
    assert "Unsupported LLM provider" in response.json()["detail"]

    unchanged_run = client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()
    assert unchanged_run["status"] == "queued"

    llm_requests = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()
    assert llm_requests == []


def test_execute_nonexistent_run_still_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        f"/agent-runs/{uuid4()}/execute-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 404
