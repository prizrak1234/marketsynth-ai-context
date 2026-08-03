"""Phase AI.22 — Chat block artifact actions."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models.agent import AgentTable
from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.models.agent_run import AgentRunTable
from app.db.models.project import ProjectTable
from app.schemas.agent_chat import AgentChatExecutionMetadata
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
from app.services.chat_block_actions import attach_block_actions
from app.services.chat_message_blocks import build_assistant_message_blocks

PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"
BANNER_MSG = "Сделай баннер для telegram канала"
MARKETING_BRIEF = {
    "title": "Launch brief",
    "body": "Positioning for Q3 launch.",
    "target_audience": "SMB founders",
    "goals": ["awareness", "signups"],
    "constraints": {"tone": "professional"},
}
CONTENT_PLAN = {
    "title": "Blog draft",
    "body": "Full article body for the launch post.",
    "summary": "Launch post outline",
}


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Block Actions"}, headers=headers)
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


def _marketing_draft_block():
    output = {"content_plan": CONTENT_PLAN}
    meta = AgentChatExecutionMetadata(entrypoint="direct_specialist", domain="marketing")
    result = build_assistant_message_blocks(
        output=output,
        execution_metadata=meta,
        fallback_text="ignored",
    )
    return result.blocks[0]


def _marketing_brief_block():
    output = {"marketing_brief": MARKETING_BRIEF}
    meta = AgentChatExecutionMetadata(entrypoint="direct_specialist", domain="marketing")
    result = build_assistant_message_blocks(
        output=output,
        execution_metadata=meta,
        fallback_text="ignored",
    )
    return result.blocks[0]


def _programmer_draft_block():
    draft = _sample_technical_task_draft()
    output = {"technical_task_draft": draft}
    meta = AgentChatExecutionMetadata(entrypoint="direct_specialist", domain="programmer")
    result = build_assistant_message_blocks(
        output=output,
        execution_metadata=meta,
        fallback_text="ignored",
    )
    return result.blocks[0]


def _media_brief_block():
    brief = _sample_visual_brief()
    output = {"visual_brief": brief}
    meta = AgentChatExecutionMetadata(entrypoint="direct_specialist", domain="media")
    result = build_assistant_message_blocks(
        output=output,
        execution_metadata=meta,
        fallback_text="ignored",
    )
    return result.blocks[0]


def _action_types(block) -> set[str]:
    return {action.type.value for action in block.actions}


def test_marketing_draft_block_exposes_create_marketing_asset() -> None:
    block = _marketing_draft_block()
    assert ChatBlockActionType.CREATE_MARKETING_ASSET.value in _action_types(block)
    assert ChatBlockActionType.COPY_TEXT.value in _action_types(block)
    assert ChatBlockActionType.EXPORT_MARKDOWN.value in _action_types(block)


def test_marketing_brief_block_exposes_create_marketing_brief() -> None:
    block = _marketing_brief_block()
    assert ChatBlockActionType.CREATE_MARKETING_BRIEF.value in _action_types(block)
    assert ChatBlockActionType.COPY_TEXT.value in _action_types(block)


def test_programmer_draft_exposes_only_copy_export_no_persistence() -> None:
    block = _programmer_draft_block()
    types = _action_types(block)
    assert ChatBlockActionType.COPY_TEXT.value in types
    assert ChatBlockActionType.EXPORT_MARKDOWN.value in types
    assert ChatBlockActionType.CREATE_MARKETING_ASSET.value not in types
    disabled = [a for a in block.actions if not a.enabled]
    assert any(a.reason and "consultation-only" in a.reason.lower() for a in disabled)


def test_media_brief_exposes_only_copy_export_no_persistence() -> None:
    block = _media_brief_block()
    types = _action_types(block)
    assert ChatBlockActionType.COPY_TEXT.value in types
    assert ChatBlockActionType.EXPORT_MARKDOWN.value in types
    assert ChatBlockActionType.CREATE_MARKETING_BRIEF.value not in types
    disabled = [a for a in block.actions if not a.enabled]
    assert any(a.reason and "consultation-only" in a.reason.lower() for a in disabled)


def _block_action(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    session_id: str,
    assistant_message_id: str,
    block_index: int,
    action_type: str,
    payload: dict | None = None,
):
    body: dict = {
        "session_id": session_id,
        "assistant_message_id": assistant_message_id,
        "block_index": block_index,
        "action_type": action_type,
    }
    if payload is not None:
        body["payload"] = payload
    return client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json=body,
        headers=headers,
    )


@pytest.mark.asyncio
async def test_create_marketing_asset_creates_draft(
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
        type=AgentType.ORCHESTRATOR,
        name="Marketer",
        status=AgentStatus.ACTIVE,
    )
    db_session.add(agent)
    await db_session.flush()

    session_row = AgentChatSessionTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        entrypoint=ChatSessionEntrypoint.DIRECT_SPECIALIST,
        domain=ChatSessionDomain.MARKETING,
        status=ChatSessionStatus.ACTIVE,
        title="Marketing chat",
    )
    db_session.add(session_row)
    await db_session.flush()

    run = AgentRunTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        status=AgentRunStatus.COMPLETED,
        input_payload={"message": "draft"},
        output_payload={"content_plan": CONTENT_PLAN},
        run_metadata={"agent_chat": True},
    )
    db_session.add(run)
    await db_session.flush()

    block = _marketing_draft_block()
    assistant = AgentChatMessageTable(
        session_id=session_row.id,
        role=AgentChatMessageRole.ASSISTANT,
        content=block.content,
        agent_run_id=run.id,
        message_metadata={
            "block_types": ["draft"],
            "domain": "marketing",
            "source_run_id": str(run.id),
            "execution_metadata": {
                "entrypoint": "direct_specialist",
                "domain": "marketing",
            },
        },
    )
    db_session.add(assistant)
    await db_session.commit()

    response = _block_action(
        client,
        auth_headers,
        project_id,
        session_id=str(session_row.id),
        assistant_message_id=str(assistant.id),
        block_index=0,
        action_type=ChatBlockActionType.CREATE_MARKETING_ASSET.value,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["created_resource_type"] == "content_asset"
    assert data["created_resource_id"]

    assets = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    )
    assert assets.status_code == 200
    items = assets.json()
    assert any(item["id"] == data["created_resource_id"] for item in items)


@pytest.mark.asyncio
async def test_missing_block_data_returns_409(
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
        type=AgentType.ORCHESTRATOR,
        name="Marketer",
        status=AgentStatus.ACTIVE,
    )
    db_session.add(agent)
    await db_session.flush()

    session_row = AgentChatSessionTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        entrypoint=ChatSessionEntrypoint.DIRECT_SPECIALIST,
        domain=ChatSessionDomain.MARKETING,
        status=ChatSessionStatus.ACTIVE,
        title="Empty",
    )
    db_session.add(session_row)
    await db_session.flush()

    fake_approved_id = uuid4()
    run = AgentRunTable(
        owner_id=project.owner_id,
        project_id=project.id,
        agent_id=agent.id,
        status=AgentRunStatus.COMPLETED,
        input_payload={},
        output_payload={
            "content_plan": CONTENT_PLAN,
            "approved_source_asset_id": str(fake_approved_id),
        },
    )
    db_session.add(run)
    await db_session.flush()

    assistant = AgentChatMessageTable(
        session_id=session_row.id,
        role=AgentChatMessageRole.ASSISTANT,
        content="Revision draft",
        agent_run_id=run.id,
        message_metadata={
            "block_types": ["draft"],
            "domain": "marketing",
            "source_run_id": str(run.id),
            "execution_metadata": {
                "entrypoint": "direct_specialist",
                "domain": "marketing",
            },
        },
    )
    db_session.add(assistant)
    await db_session.commit()

    response = _block_action(
        client,
        auth_headers,
        project_id,
        session_id=str(session_row.id),
        assistant_message_id=str(assistant.id),
        block_index=0,
        action_type=ChatBlockActionType.CREATE_REVISION_FROM_APPROVED.value,
    )
    assert response.status_code == 409
    assert "enough data" in response.json()["detail"].lower()


def test_action_endpoint_rejects_forged_persistence_for_media(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": BANNER_MSG, "agent_id": media_id},
        headers=auth_headers,
    ).json()
    response = _block_action(
        client,
        auth_headers,
        project_id,
        session_id=body["session_id"],
        assistant_message_id=body["assistant_message_id"],
        block_index=0,
        action_type=ChatBlockActionType.CREATE_MARKETING_ASSET.value,
    )
    assert response.status_code == 409


def test_action_endpoint_rejects_forged_persistence_for_programmer(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()
    response = _block_action(
        client,
        auth_headers,
        project_id,
        session_id=body["session_id"],
        assistant_message_id=body["assistant_message_id"],
        block_index=0,
        action_type=ChatBlockActionType.CREATE_MARKETING_BRIEF.value,
    )
    assert response.status_code == 409


def test_action_endpoint_validates_owner_project_session_message(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()

    wrong_owner = _block_action(
        client,
        other_auth_headers,
        project_id,
        session_id=body["session_id"],
        assistant_message_id=body["assistant_message_id"],
        block_index=0,
        action_type=ChatBlockActionType.COPY_TEXT.value,
    )
    assert wrong_owner.status_code == 404

    wrong_session = _block_action(
        client,
        auth_headers,
        project_id,
        session_id=str(uuid4()),
        assistant_message_id=body["assistant_message_id"],
        block_index=0,
        action_type=ChatBlockActionType.COPY_TEXT.value,
    )
    assert wrong_session.status_code == 404


def test_copy_text_returns_readable_content(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()
    response = _block_action(
        client,
        auth_headers,
        project_id,
        session_id=body["session_id"],
        assistant_message_id=body["assistant_message_id"],
        block_index=0,
        action_type=ChatBlockActionType.COPY_TEXT.value,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["text"]
    assert "{" not in data["text"][:20]


def test_export_markdown_returns_markdown(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": BANNER_MSG, "agent_id": media_id},
        headers=auth_headers,
    ).json()
    response = _block_action(
        client,
        auth_headers,
        project_id,
        session_id=body["session_id"],
        assistant_message_id=body["assistant_message_id"],
        block_index=0,
        action_type=ChatBlockActionType.EXPORT_MARKDOWN.value,
    )
    assert response.status_code == 200
    assert response.json()["markdown"]


def test_message_metadata_stores_source_run_id_not_full_drafts(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()
    metadata = body["assistant_message"]["metadata"]
    assert metadata.get("source_run_id")
    assert metadata["source_run_id"] == body["agent_run_id"]
    assert "technical_task_draft" not in metadata


def test_send_response_blocks_include_actions(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()
    block = body["blocks"][0]
    assert block.get("actions")
    assert any(a["type"] == "copy_text" and a["enabled"] for a in block["actions"])


def test_clarification_block_has_copy_only(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": BANNER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()
    block = body["blocks"][0]
    assert block["type"] == "clarification"
    types = {a["type"] for a in block["actions"]}
    assert "copy_text" in types
    assert "create_marketing_asset" not in types or not any(
        a["type"] == "create_marketing_asset" and a["enabled"] for a in block["actions"]
    )


def test_revision_action_when_approved_source_in_data() -> None:
    block = attach_block_actions(
        _marketing_draft_block().model_copy(
            update={
                "data": {
                    "content_plan": CONTENT_PLAN,
                    "approved_source_asset_id": str(uuid4()),
                },
            },
        ),
    )
    assert ChatBlockActionType.CREATE_REVISION_FROM_APPROVED.value in _action_types(block)
