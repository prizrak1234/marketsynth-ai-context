"""Phase AI.24 — Chat search + session filters."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.agent import AgentTable
from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.models.agent_run import AgentRunTable
from app.db.models.project import ProjectTable
from app.schemas.contracts import (
    AgentChatMessageRole,
    AgentRunStatus,
    AgentStatus,
    AgentType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionStatus,
)
from app.core.exceptions import InvalidStateError
from app.services.chat_search import (
    build_like_pattern,
    build_search_content_preview,
    escape_like_pattern,
    prepare_search_query,
)

PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"
UNIQUE_TITLE = "Webhook integration planning"
UNIQUE_BODY = "Retry policy for outbound webhooks"
METADATA_ONLY_TOKEN = "meta-only-token-xyzzy-24"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Chat Search"}, headers=headers)
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
    if session_id:
        payload["session_id"] = session_id
    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_search_sessions_by_title(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=UNIQUE_TITLE,
    )
    session = (
        await db_session.execute(
            select(AgentChatSessionTable).where(
                AgentChatSessionTable.id == UUID(body["session_id"]),
            ),
        )
    ).scalar_one()
    session.title = UNIQUE_TITLE
    db_session.add(session)
    await db_session.commit()

    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"query": "Webhook", "agent_id": programmer_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert any(UNIQUE_TITLE in (item.get("title") or "") for item in data)


@pytest.mark.asyncio
async def test_search_sessions_by_message_content(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=UNIQUE_BODY,
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"query": "Retry policy", "agent_id": programmer_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert any(item["id"] == body["session_id"] for item in response.json())


def test_filter_sessions_by_domain(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")
    prog_chat = _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_MSG,
    )
    _chat(client, auth_headers, project_id, agent_id=media_id, content="Banner brief")

    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"domain": "programmer", "agent_id": programmer_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert all(item["domain"] == "programmer" for item in data)
    assert any(item["id"] == prog_chat["session_id"] for item in data)


def test_filter_sessions_by_entrypoint(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)

    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"entrypoint": "direct_specialist", "agent_id": programmer_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert all(item["entrypoint"] == "direct_specialist" for item in response.json())


def test_active_default_excludes_archived_unless_requested(
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
    )
    archive = client.post(
        f"/projects/{project_id}/agent-chat/sessions/{body['session_id']}/archive",
        headers=auth_headers,
    )
    assert archive.status_code == 200

    active_only = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"agent_id": programmer_id},
        headers=auth_headers,
    )
    assert active_only.status_code == 200
    assert not any(item["id"] == body["session_id"] for item in active_only.json())

    archived = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"agent_id": programmer_id, "status": "archived"},
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert any(item["id"] == body["session_id"] for item in archived.json())


def test_search_messages_returns_previews(
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
        content=UNIQUE_BODY,
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": "Retry policy", "agent_id": programmer_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    hits = response.json()
    assert len(hits) >= 1
    hit = hits[0]
    assert hit["message_id"]
    assert hit["session_id"] == body["session_id"]
    assert hit["content_preview"]
    assert len(hit["content_preview"]) <= 200
    assert "Retry policy" in hit["content_preview"] or "webhook" in hit["content_preview"].lower()


def test_search_messages_respects_session_id(
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
        content="Alpha unique token one",
    )
    _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content="Beta unique token two",
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={
            "query": "unique token",
            "session_id": first["session_id"],
            "agent_id": programmer_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert all(hit["session_id"] == first["session_id"] for hit in response.json())


def test_search_messages_respects_role(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content="Role filter marker phrase",
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={
            "query": "marker phrase",
            "role": "user",
            "agent_id": programmer_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert all(hit["role"] == "user" for hit in response.json())


def test_query_min_length_validation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    short_session = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"query": "a"},
        headers=auth_headers,
    )
    assert short_session.status_code == 422

    short_message = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": "x"},
        headers=auth_headers,
    )
    assert short_message.status_code == 422


def test_query_max_length_validation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    long_query = "x" * 121
    session_resp = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"query": long_query},
        headers=auth_headers,
    )
    assert session_resp.status_code == 422

    message_resp = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": long_query},
        headers=auth_headers,
    )
    assert message_resp.status_code == 422


def test_like_wildcard_escaping(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    assert escape_like_pattern("100%") == "100\\%"
    pattern = build_like_pattern("100%")
    assert "%" in pattern
    assert "\\%" in pattern or "100\\%" in pattern

    with pytest.raises(InvalidStateError):
        prepare_search_query("x" * 121, required=True)


@pytest.mark.asyncio
async def test_percent_wildcard_does_not_match_all_messages(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    project = (
        await db_session.execute(
            select(ProjectTable).where(ProjectTable.id == UUID(project_id)),
        )
    ).scalar_one()
    agent = AgentTable(
        project_id=project.id,
        owner_id=project.owner_id,
        type=AgentType.PROGRAMMER,
        name="P",
        status=AgentStatus.ACTIVE,
    )
    db_session.add(agent)
    await db_session.flush()

    session_row = AgentChatSessionTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        entrypoint=ChatSessionEntrypoint.DIRECT_SPECIALIST,
        domain=ChatSessionDomain.PROGRAMMER,
        status=ChatSessionStatus.ACTIVE,
        title="Percent test",
    )
    db_session.add(session_row)
    await db_session.flush()

    db_session.add(
        AgentChatMessageTable(
            session_id=session_row.id,
            role=AgentChatMessageRole.USER,
            content="Progress is 100% complete for rollout",
            message_metadata={},
        ),
    )
    db_session.add(
        AgentChatMessageTable(
            session_id=session_row.id,
            role=AgentChatMessageRole.ASSISTANT,
            content="Unrelated assistant reply without percent sign",
            message_metadata={},
        ),
    )
    await db_session.commit()

    hit = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": "100%", "agent_id": str(agent.id)},
        headers=auth_headers,
    )
    assert hit.status_code == 200
    assert len(hit.json()) >= 1

    bare_percent = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": "%", "agent_id": str(agent.id)},
        headers=auth_headers,
    )
    assert bare_percent.status_code == 422


@pytest.mark.asyncio
async def test_no_metadata_search_exposure(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    project = (
        await db_session.execute(
            select(ProjectTable).where(ProjectTable.id == UUID(project_id)),
        )
    ).scalar_one()
    agent = AgentTable(
        project_id=project.id,
        owner_id=project.owner_id,
        type=AgentType.PROGRAMMER,
        name="P",
        status=AgentStatus.ACTIVE,
    )
    db_session.add(agent)
    await db_session.flush()

    session_row = AgentChatSessionTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        entrypoint=ChatSessionEntrypoint.DIRECT_SPECIALIST,
        domain=ChatSessionDomain.PROGRAMMER,
        status=ChatSessionStatus.ACTIVE,
        title="Metadata isolation",
    )
    db_session.add(session_row)
    await db_session.flush()

    run = AgentRunTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        status=AgentRunStatus.COMPLETED,
        input_payload={},
        output_payload={"secret": METADATA_ONLY_TOKEN},
    )
    db_session.add(run)
    await db_session.flush()

    db_session.add(
        AgentChatMessageTable(
            session_id=session_row.id,
            role=AgentChatMessageRole.ASSISTANT,
            content="Visible line without the metadata token",
            agent_run_id=run.id,
            message_metadata={
                "source_run_id": str(run.id),
                "block_types": ["text"],
                "domain": "programmer",
                "nested": METADATA_ONLY_TOKEN,
            },
        ),
    )
    await db_session.commit()

    response = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": METADATA_ONLY_TOKEN, "agent_id": str(agent.id)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []

    sessions = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"query": METADATA_ONLY_TOKEN, "agent_id": str(agent.id)},
        headers=auth_headers,
    )
    assert sessions.status_code == 200
    assert sessions.json() == []


def test_limit_max_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    sessions = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"limit": 200},
        headers=auth_headers,
    )
    assert sessions.status_code == 422

    messages = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": "test", "limit": 100},
        headers=auth_headers,
    )
    assert messages.status_code == 422


def test_search_hit_has_no_raw_payload_fields(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    _chat(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content="Payload exposure check phrase",
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": "exposure check", "agent_id": programmer_id},
        headers=auth_headers,
    )
    assert response.status_code == 200
    blob = json.dumps(response.json()).lower()
    assert "output_payload" not in blob
    assert "message_metadata" not in blob


def test_prepare_search_query_unit() -> None:
    assert prepare_search_query("  ab  ", required=True) == "ab"
    with pytest.raises(InvalidStateError):
        prepare_search_query("a", required=True)


def test_preview_max_length() -> None:
    preview = build_search_content_preview("word " * 80)
    assert len(preview) <= 200
