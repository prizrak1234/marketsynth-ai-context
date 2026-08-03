"""Phase AI.23 — Rebuild assistant blocks on chat history."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

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
    ChatBlockActionType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionStatus,
)

PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"
BANNER_MSG = "Сделай баннер для telegram канала"
CONTENT_PLAN = {
    "title": "Blog draft",
    "body": "Full article body for the launch post.",
    "summary": "Launch post outline",
}
MARKETING_BRIEF = {
    "title": "Launch brief",
    "body": "Positioning for Q3 launch.",
    "target_audience": "SMB founders",
}


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "History Blocks"}, headers=headers)
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


def _sample_technical_task_draft() -> dict:
    return {
        "kind": "technical_task_draft",
        "title": "Technical task draft (consultation)",
        "summary": PROGRAMMER_MSG,
        "scope": "Consultation-only skeleton.",
        "deliverables": ["Problem statement", "API outline"],
        "assistant_excerpt": "Outline webhook handler and retry policy.",
        "persisted": False,
    }


def _sample_visual_brief() -> dict:
    return {
        "format": "banner",
        "concept": "Telegram channel promo",
        "composition": "Hero left, CTA right",
        "text_overlay": "Join the channel",
        "style_notes": "Bold contrast",
        "persisted": False,
    }


def _action_types(block: dict) -> set[str]:
    return {action["type"] for action in block.get("actions", [])}


@pytest.mark.asyncio
async def _seed_history_message(
    db_session: AsyncSession,
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    agent_type: str,
    output_payload: dict,
    domain: str,
    block_types: list[str],
    content: str,
    source_run_id: UUID | None = None,
    include_source_run_in_metadata: bool = True,
    link_agent_run_on_message: bool = True,
) -> tuple[str, str, str, str]:
    project_id = _create_project(client, auth_headers)
    project = (
        await db_session.execute(
            select(ProjectTable).where(ProjectTable.id == UUID(project_id)),
        )
    ).scalar_one()

    agent = AgentTable(
        project_id=project.id,
        owner_id=project.owner_id,
        type=AgentType(agent_type),
        name="Agent",
        status=AgentStatus.ACTIVE,
    )
    db_session.add(agent)
    await db_session.flush()

    session_row = AgentChatSessionTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        entrypoint=ChatSessionEntrypoint.DIRECT_SPECIALIST,
        domain=ChatSessionDomain(domain),
        status=ChatSessionStatus.ACTIVE,
        title="History",
    )
    db_session.add(session_row)
    await db_session.flush()

    run = AgentRunTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        status=AgentRunStatus.COMPLETED,
        input_payload={"message": "test"},
        output_payload=output_payload,
    )
    db_session.add(run)
    await db_session.flush()

    effective_run_id = source_run_id or run.id
    metadata: dict = {
        "block_types": block_types,
        "domain": domain,
        "execution_metadata": {
            "entrypoint": "direct_specialist",
            "domain": domain,
        },
    }
    if include_source_run_in_metadata:
        metadata["source_run_id"] = str(effective_run_id)

    db_session.add(
        AgentChatMessageTable(
            session_id=session_row.id,
            role=AgentChatMessageRole.USER,
            content="user question",
            message_metadata={},
        ),
    )
    assistant = AgentChatMessageTable(
        session_id=session_row.id,
        role=AgentChatMessageRole.ASSISTANT,
        content=content,
        agent_run_id=run.id if link_agent_run_on_message else None,
        message_metadata=metadata,
    )
    db_session.add(assistant)
    await db_session.commit()

    return project_id, str(session_row.id), str(assistant.id), str(effective_run_id)


@pytest.mark.asyncio
async def test_get_messages_returns_rebuilt_programmer_draft_block(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    draft = _sample_technical_task_draft()
    project_id, session_id, _, _ = await _seed_history_message(
        db_session,
        client,
        auth_headers,
        agent_type="programmer",
        output_payload={"technical_task_draft": draft},
        domain="programmer",
        block_types=["draft"],
        content="Readable programmer summary",
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert response.status_code == 200
    messages = response.json()
    assistant = next(m for m in messages if m["role"] == "assistant")
    assert assistant["blocks"]
    block = assistant["blocks"][0]
    assert block["type"] == "draft"
    assert block["domain"] == "programmer"
    assert block["persisted"] is False
    assert "{" not in block["content"][:20]


@pytest.mark.asyncio
async def test_get_messages_returns_rebuilt_media_brief_block(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    brief = _sample_visual_brief()
    project_id, session_id, _, _ = await _seed_history_message(
        db_session,
        client,
        auth_headers,
        agent_type="media",
        output_payload={"visual_brief": brief},
        domain="media",
        block_types=["brief"],
        content="Readable media summary",
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assistant = next(m for m in response.json() if m["role"] == "assistant")
    assert assistant["blocks"][0]["type"] == "brief"
    assert assistant["blocks"][0]["domain"] == "media"


@pytest.mark.asyncio
async def test_get_messages_returns_marketing_block_with_actions(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id, session_id, _, _ = await _seed_history_message(
        db_session,
        client,
        auth_headers,
        agent_type="orchestrator",
        output_payload={"content_plan": CONTENT_PLAN},
        domain="marketing",
        block_types=["draft"],
        content="Marketing draft body",
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assistant = next(m for m in response.json() if m["role"] == "assistant")
    block = assistant["blocks"][0]
    assert block["domain"] == "marketing"
    assert ChatBlockActionType.CREATE_MARKETING_ASSET.value in _action_types(block)
    assert ChatBlockActionType.COPY_TEXT.value in _action_types(block)


def test_programmer_history_blocks_only_copy_export(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()
    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{chat['session_id']}/messages",
        headers=auth_headers,
    ).json()
    assistant = next(m for m in messages if m["role"] == "assistant")
    types = _action_types(assistant["blocks"][0])
    assert "copy_text" in types
    assert "export_markdown" in types
    assert "create_marketing_asset" not in types or not any(
        a["type"] == "create_marketing_asset" and a["enabled"]
        for a in assistant["blocks"][0]["actions"]
    )


@pytest.mark.asyncio
async def test_missing_source_run_id_falls_back_to_text_block(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id, session_id, _, _ = await _seed_history_message(
        db_session,
        client,
        auth_headers,
        agent_type="programmer",
        output_payload={"technical_task_draft": _sample_technical_task_draft()},
        domain="programmer",
        block_types=["draft"],
        content="Legacy readable text only",
        include_source_run_in_metadata=False,
        link_agent_run_on_message=False,
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assistant = next(m for m in response.json() if m["role"] == "assistant")
    assert assistant["blocks"][0]["type"] == "text"
    assert assistant["blocks"][0]["content"] == "Legacy readable text only"
    assert "copy_text" in _action_types(assistant["blocks"][0])


@pytest.mark.asyncio
async def test_deleted_source_run_id_falls_back_without_500(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id, session_id, _, _ = await _seed_history_message(
        db_session,
        client,
        auth_headers,
        agent_type="programmer",
        output_payload={"technical_task_draft": _sample_technical_task_draft()},
        domain="programmer",
        block_types=["draft"],
        content="Fallback after missing run",
        source_run_id=uuid4(),
    )
    response = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assistant = next(m for m in response.json() if m["role"] == "assistant")
    assert assistant["blocks"][0]["type"] == "text"


def test_user_messages_return_empty_blocks(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()
    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{chat['session_id']}/messages",
        headers=auth_headers,
    ).json()
    user = next(m for m in messages if m["role"] == "user")
    assert user["blocks"] == []


def test_message_list_order_asc(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    session_id = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()["session_id"]
    client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Second message", "agent_id": programmer_id, "session_id": session_id},
        headers=auth_headers,
    )
    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    ).json()
    timestamps = [m["created_at"] for m in messages]
    assert timestamps == sorted(timestamps)


def test_limit_default_and_max(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    session_id = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()["session_id"]
    for index in range(3):
        client.post(
            f"/projects/{project_id}/agent-chat",
            json={
                "content": f"Message {index}",
                "agent_id": programmer_id,
                "session_id": session_id,
            },
            headers=auth_headers,
        )
    default_resp = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert default_resp.status_code == 200
    assert len(default_resp.json()) <= 50

    limited = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages?limit=2",
        headers=auth_headers,
    )
    assert limited.status_code == 200
    assert len(limited.json()) == 2

    too_high = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{session_id}/messages?limit=200",
        headers=auth_headers,
    )
    assert too_high.status_code == 422


def test_no_raw_output_payload_in_message_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": BANNER_MSG, "agent_id": media_id},
        headers=auth_headers,
    ).json()
    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{chat['session_id']}/messages",
        headers=auth_headers,
    ).json()
    assistant = next(m for m in messages if m["role"] == "assistant")
    metadata_blob = json.dumps(assistant["metadata"]).lower()
    assert "output_payload" not in metadata_blob
    assert "technical_task_draft" not in metadata_blob
    assert "visual_brief" not in metadata_blob
    assert assistant["blocks"]
    assert assistant["blocks"][0].get("data") is not None or assistant["blocks"][0]["type"] in (
        "brief",
        "draft",
        "text",
    )
