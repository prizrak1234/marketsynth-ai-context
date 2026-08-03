"""Phase AI.20 — Chat session title + UX readiness."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.schemas.contracts import AgentChatMessageRole, ChatSessionDomain
from app.services.chat_session_preview import (
    SESSION_PREVIEW_MAX_LENGTH,
    build_message_preview,
    build_preview_from_message,
)
from app.services.chat_session_title import (
    SESSION_TITLE_MAX_LENGTH,
    build_session_title,
    collapse_message_line,
)
from fastapi.testclient import TestClient

PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"
PROGRAMMER_MSG_B = "Вторая реплика в сессии"
BANNER_MSG = "Сделай баннер для telegram канала"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Session UX"}, headers=headers)
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
):
    payload: dict[str, str] = {"content": content, "agent_id": agent_id}
    if session_id:
        payload["session_id"] = session_id
    return client.post(
        f"/projects/{project_id}/agent-chat",
        json=payload,
        headers=headers,
    )


def test_title_generated_from_first_user_message() -> None:
    title = build_session_title(
        first_message="  Hello\nworld  ",
        domain=ChatSessionDomain.PROGRAMMER,
    )
    assert title == "Hello world"


def test_title_fallback_by_domain() -> None:
    assert (
        build_session_title(first_message="   ", domain=ChatSessionDomain.UNKNOWN)
        == "General chat"
    )
    assert (
        build_session_title(first_message="", domain=ChatSessionDomain.MARKETING)
        == "Marketing chat"
    )
    assert (
        build_session_title(first_message="", domain=ChatSessionDomain.PROGRAMMER)
        == "Programmer chat"
    )
    assert (
        build_session_title(first_message="", domain=ChatSessionDomain.MEDIA) == "Media chat"
    )


def test_title_max_length() -> None:
    long_text = "a" * 120
    title = build_session_title(first_message=long_text, domain=ChatSessionDomain.MEDIA)
    assert len(title) <= SESSION_TITLE_MAX_LENGTH + 1
    assert title.endswith("…")


def test_multiline_title_collapsed() -> None:
    assert collapse_message_line("line1\nline2\r\nline3") == "line1 line2 line3"


def test_preview_max_160_chars() -> None:
    preview = build_message_preview("z" * 200)
    assert preview is not None
    assert len(preview) <= SESSION_PREVIEW_MAX_LENGTH + 1
    assert preview.endswith("…")


def test_preview_excludes_draft_and_tool_markers() -> None:
    assert build_message_preview('{"technical_task_draft": {"persisted": false}}') is None
    assert build_message_preview("tool_logs: [{name: shell.execute}]") is None


def test_sessions_sorted_by_last_message_at_desc(
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
    _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG_B,
        session_id=first["session_id"],
    )

    second_session = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content="Совсем другая новая сессия для сортировки",
    ).json()

    listed = client.get(
        f"/projects/{project_id}/agent-chat/sessions?agent_id={programmer_id}",
        headers=auth_headers,
    ).json()
    assert len(listed) >= 2
    assert listed[0]["id"] == second_session["session_id"]
    assert listed[0]["last_message_at"] is not None


def test_message_count_and_unread_count(
    client: TestClient,
    auth_headers: dict[str, str],
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

    listed = client.get(
        f"/projects/{project_id}/agent-chat/sessions?agent_id={programmer_id}",
        headers=auth_headers,
    ).json()
    row = next(item for item in listed if item["id"] == body["session_id"])
    assert row["message_count"] == 2
    assert row["unread_count"] == 0
    assert row["last_message_preview"]


def test_updated_at_changes_after_append(
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
    updated_after_first = first["session"]["updated_at"]

    second = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG_B,
        session_id=first["session_id"],
    ).json()
    assert second["session"]["updated_at"] >= updated_after_first


def test_archive_updates_status_and_timestamp(
    client: TestClient,
    auth_headers: dict[str, str],
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
    before = body["session"]["updated_at"]

    archived = client.post(
        f"/projects/{project_id}/agent-chat/sessions/{body['session_id']}/archive",
        headers=auth_headers,
    ).json()
    assert archived["status"] == "archived"
    assert archived["updated_at"] >= before


def test_api_title_from_first_message(
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
    assert BANNER_MSG[:40] in (body["session"]["title"] or "")


def test_preview_uses_role_content_only() -> None:
    from app.db.models.agent_chat import AgentChatMessageTable

    message = AgentChatMessageTable(
        session_id=uuid4(),
        role=AgentChatMessageRole.ASSISTANT,
        content="Short assistant reply",
        message_metadata={"tools": ["plan_draft"], "technical_task_draft": {"x": 1}},
    )
    assert build_preview_from_message(message) == "Short assistant reply"
