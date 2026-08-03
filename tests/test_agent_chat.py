"""Agent chat API tests (Phase AI.1)."""

from __future__ import annotations

import pytest
from app.core.exceptions import ExecutorError
from app.tools.write_tool_settings import is_real_write_executable
from fastapi.testclient import TestClient


def _create_project(client: TestClient, headers: dict[str, str], name: str = "Chat Project") -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_strategist(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_session_on_first_message(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Hello, what can you help with?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session"]["project_id"] == project_id
    assert body["session"]["title"].startswith("Hello")
    assert body["user_message"]["role"] == "user"
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["content"]
    assert body["agent_run_id"]

    sessions = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        headers=auth_headers,
    )
    assert sessions.status_code == 200
    assert len(sessions.json()) == 1
    assert sessions.json()[0]["id"] == body["session"]["id"]


def test_append_message_to_existing_session(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    first = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "First turn"},
        headers=auth_headers,
    ).json()
    session_id = first["session"]["id"]

    second = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Second turn", "session_id": session_id},
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert second.json()["session"]["id"] == session_id

    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert messages.status_code == 200
    roles = [item["role"] for item in messages.json()]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_agent_run_is_created_and_succeeds(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Run check"},
        headers=auth_headers,
    ).json()
    run_id = sent["agent_run_id"]

    run = client.get(f"/agent-runs/{run_id}", headers=auth_headers)
    assert run.status_code == 200
    assert run.json()["status"] == "succeeded"
    assert run.json()["output_payload"]["content"]
    assert sent["assistant_message"]["agent_run_id"] == run_id


def test_assistant_message_persisted(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Persist assistant"},
        headers=auth_headers,
    ).json()
    session_id = sent["session"]["id"]
    assistant_id = sent["assistant_message"]["id"]

    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    ).json()
    assistant = next(item for item in messages if item["id"] == assistant_id)
    assert assistant["role"] == "assistant"
    assert assistant["content"] == sent["assistant_message"]["content"]


def test_foreign_project_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Should not send"},
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_foreign_session_messages_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)
    session_id = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Private session"},
        headers=auth_headers,
    ).json()["session"]["id"]

    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_pii_sanitizer_on_stored_messages(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)
    raw = "Reach me at user@example.com or +79991234567"

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": raw},
        headers=auth_headers,
    ).json()
    user_content = sent["user_message"]["content"]
    assert "user@example.com" not in user_content
    assert "+79991234567" not in user_content
    assert "[EMAIL]" in user_content
    assert "[PHONE]" in user_content


def test_no_write_tools_executed(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CAMPAIGN_PLAN_DRAFT_CREATE_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "No tools please"},
        headers=auth_headers,
    ).json()
    run_id = sent["agent_run_id"]

    logs = client.get(f"/agent-runs/{run_id}/tool-executions", headers=auth_headers)
    assert logs.status_code == 200
    for entry in logs.json():
        assert not is_real_write_executable(entry["tool_name"])


def test_llm_unavailable_returns_safe_error(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = _create_project(client, auth_headers)
    _create_strategist(client, auth_headers, project_id)

    async def _fail_execute(*_args, **_kwargs):
        raise ExecutorError("provider down")

    monkeypatch.setattr(
        "app.services.agent_chat_service.AgentRunCoordinator.execute_run",
        _fail_execute,
    )

    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "This should fail safely"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Agent temporarily unavailable"
