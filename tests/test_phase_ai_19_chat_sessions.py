"""Phase AI.19 — Specialist chat sessions + history boundary."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.agents.direct_specialist.contracts import ENTRYPOINT_DIRECT_SPECIALIST
from app.agents.general.execution import ENTRYPOINT_GENERAL_DELEGATION
from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import AgentType, ChatSessionStatus
from app.services.agent_runs import AgentRunService
from app.services.chat_session_history import (
    assert_history_safe_for_prompt,
    build_session_history_for_run,
)
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from fastapi.testclient import TestClient

PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"
PROGRAMMER_MSG_2 = "Добавь retry logic для webhook"
BANNER_MSG = "Сделай баннер для telegram канала"
GENERAL_PROGRAMMER_MSG = PROGRAMMER_MSG
LAUNCH_MESSAGE = "Запусти новый продукт"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Chat Sessions"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_agent(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_type: str,
) -> str:
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": agent_type},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _chat(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_id: str,
    content: str,
    session_id: str | None = None,
) -> dict:
    payload: dict[str, str] = {"content": content, "agent_id": agent_id}
    if session_id is not None:
        payload["session_id"] = session_id
    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json=payload,
        headers=headers,
    )
    return response


def test_new_direct_programmer_chat_creates_session_and_messages(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    response = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == body["session"]["id"]
    assert body["assistant_message_id"] == body["assistant_message"]["id"]
    assert body["session"]["entrypoint"] == ENTRYPOINT_DIRECT_SPECIALIST
    assert body["session"]["domain"] == "programmer"
    assert body["session"]["status"] == "active"
    assert body["session"]["agent_id"] == programmer_id

    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{body['session_id']}/messages",
        headers=auth_headers,
    ).json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_continuing_programmer_session_appends_messages(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    first = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG,
    ).json()
    second = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG_2,
        session_id=first["session_id"],
    )
    assert second.status_code == 200
    body = second.json()
    assert body["session_id"] == first["session_id"]

    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{body['session_id']}/messages",
        headers=auth_headers,
    ).json()
    assert len(messages) == 4

    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    history = run["input_payload"].get("messages") or []
    assert len(history) >= 2
    assert history[-1]["role"] == "user"
    assert PROGRAMMER_MSG_2 in history[-1]["content"]


def test_direct_media_session_preserves_visual_brief_not_persisted(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")

    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=media_id,
        content=BANNER_MSG,
    ).json()
    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    brief = (run.get("output_payload") or {}).get("visual_brief")
    assert brief is not None
    assert brief["persisted"] is False


def test_general_session_entrypoint_and_delegation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="programmer")

    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=general_id,
        content=GENERAL_PROGRAMMER_MSG,
    ).json()
    assert body["session"]["entrypoint"] == ENTRYPOINT_GENERAL_DELEGATION
    assert body["execution_metadata"]["entrypoint"] == ENTRYPOINT_GENERAL_DELEGATION
    assert body["general_delegation"]["domain"] == "programmer"


def test_wrong_owner_cannot_access_session(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG,
    ).json()

    denied = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{body['session_id']}/messages",
        headers=other_auth_headers,
    )
    assert denied.status_code == 404


def test_wrong_agent_cannot_continue_session(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")

    first = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG,
    ).json()

    conflict = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=media_id,
        content=BANNER_MSG,
        session_id=first["session_id"],
    )
    assert conflict.status_code == 422


def test_archived_session_cannot_continue(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    first = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG,
    ).json()

    archived = client.post(
        f"/projects/{project_id}/agent-chat/sessions/{first['session_id']}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == ChatSessionStatus.ARCHIVED.value

    blocked = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG_2,
        session_id=first["session_id"],
    )
    assert blocked.status_code == 422


def test_recent_history_limited_to_n(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_CHAT_SESSION_HISTORY_LIMIT", "10")
    get_settings.cache_clear()

    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    session_id: str | None = None
    last_body: dict | None = None
    for index in range(12):
        response = _chat(
            client,
            auth_headers,
            project_id,
            agent_id=programmer_id,
            content=f"{PROGRAMMER_MSG} turn {index}",
            session_id=session_id,
        )
        assert response.status_code == 200
        last_body = response.json()
        session_id = last_body["session_id"]

    assert last_body is not None
    run = client.get(f"/agent-runs/{last_body['agent_run_id']}", headers=auth_headers).json()
    history = run["input_payload"].get("messages") or []
    assert len(history) <= 10


def test_history_context_excludes_forbidden_keys() -> None:
    history = build_session_history_for_run(
        [],
        current_user_content="hello",
        limit=10,
    )
    assert_history_safe_for_prompt(history)
    for item in history:
        assert "tool_logs" not in item
        assert "config" not in item
        assert "api_key" not in item


def test_programmer_media_tool_allowlists_remain_empty() -> None:
    assert get_agent_tool_allowlist(AgentType.PROGRAMMER) == frozenset()
    assert get_agent_tool_allowlist(AgentType.MEDIA) == frozenset()


@pytest.mark.asyncio
async def test_programmer_direct_still_cannot_spawn_children(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_agent_id = UUID(
        _create_agent(client, auth_headers, project_id, agent_type="programmer"),
    )
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=str(programmer_agent_id),
        content=PROGRAMMER_MSG,
    ).json()
    owner_id = UUID(body["session"]["owner_id"])
    run = await AgentRunService(db_session).get_run(owner_id, UUID(body["agent_run_id"]))
    assert run is not None

    with pytest.raises(InvalidStateError, match="cannot spawn child runs"):
        await AgentRunService(db_session).create_run(
            owner_id,
            agent_id=programmer_agent_id,
            task_id=run.task_id,
            input_payload={"prompt": "nested"},
            metadata={},
            parent_agent_run_id=run.id,
        )


def test_list_sessions_filter_by_agent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")

    _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    _chat(client, auth_headers, project_id, agent_id=media_id, content=BANNER_MSG)

    programmer_sessions = client.get(
        f"/projects/{project_id}/agent-chat/sessions?agent_id={programmer_id}",
        headers=auth_headers,
    ).json()
    assert len(programmer_sessions) >= 1
    assert all(row["agent_id"] == programmer_id for row in programmer_sessions)


def test_chat_alias_post_path(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    response = client.post(
        f"/projects/{project_id}/chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["session"]["domain"] == "programmer"
