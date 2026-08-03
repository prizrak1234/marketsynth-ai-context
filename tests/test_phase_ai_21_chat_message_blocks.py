"""Phase AI.21 — Chat message contracts + frontend-safe rendering."""

from __future__ import annotations

import json
from uuid import uuid4

from app.agents.direct_specialist.prompts import PROGRAMMER_DIRECT_CLARIFICATION
from app.agents.general.prompts import UNKNOWN_DOMAIN_CLARIFICATION
from app.schemas.agent_chat import AgentChatExecutionMetadata
from app.services.chat_message_blocks import (
    build_assistant_message_blocks,
    build_safe_error_block,
    format_technical_task_summary,
)
from app.services.chat_session_preview import (
    build_message_preview,
    build_preview_from_message,
)
from fastapi.testclient import TestClient

PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"
BANNER_MSG = "Сделай баннер для telegram канала"
UNKNOWN_MSG = "Как настроить PostgreSQL replication?"
LAUNCH_MSG = "Запусти новый продукт"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Message Blocks"}, headers=headers)
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


def test_programmer_response_includes_draft_block() -> None:
    draft = _sample_technical_task_draft()
    output = {"content": "Outline webhook handler.", "technical_task_draft": draft}
    meta = AgentChatExecutionMetadata(
        entrypoint="direct_specialist",
        domain="programmer",
    )
    result = build_assistant_message_blocks(
        output=output,
        execution_metadata=meta,
        fallback_text="ignored",
    )
    assert len(result.blocks) == 1
    block = result.blocks[0]
    assert block.type.value == "draft"
    assert block.domain.value == "programmer"
    assert block.title == "Technical task draft"
    assert block.persisted is False
    assert block.data is not None
    assert block.data.get("technical_task_draft") == draft
    assert "{" not in block.content[:20]


def test_programmer_readable_content_not_json_dump(
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
    assistant = body["assistant_message"]
    assert not assistant["content"].lstrip().startswith("{")
    assert "technical_task_draft" not in assistant["content"]
    blocks = body["blocks"]
    assert any(block["type"] == "draft" for block in blocks)
    assert blocks[0]["data"]["technical_task_draft"]["persisted"] is False


def test_media_response_includes_brief_block(
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
    blocks = body["blocks"]
    assert any(block["type"] == "brief" and block["domain"] == "media" for block in blocks)
    brief_block = next(block for block in blocks if block["type"] == "brief")
    assert brief_block["title"] == "Visual brief"
    assert brief_block["persisted"] is False
    assert "visual_brief" in brief_block["data"]


def test_general_unknown_clarification_block(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": UNKNOWN_MSG, "agent_id": general_id},
        headers=auth_headers,
    ).json()
    blocks = body["blocks"]
    assert len(blocks) >= 1
    assert blocks[0]["type"] == "clarification"
    assert blocks[0]["domain"] == "unknown"
    assert UNKNOWN_DOMAIN_CLARIFICATION in blocks[0]["content"]


def test_marketing_maps_to_safe_text_block(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")
    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Перепиши этот пост", "agent_id": orchestrator_id},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    blocks = body.get("blocks") or []
    assert len(blocks) >= 1
    assert any(
        block["type"] in ("text", "draft", "brief", "marketing_plan") for block in blocks
    )
    assert body["assistant_message"]["content"]
    assert not body["assistant_message"]["content"].lstrip().startswith("{")


def test_error_block_strips_stack_and_raw_payload() -> None:
    block = build_safe_error_block(
        "Traceback (most recent call last):\n  File secret.py\napi_key=sk-xxx",
    )
    assert block.type.value == "error"
    assert "traceback" not in block.content.lower()
    assert "api_key" not in block.content.lower()
    assert "sk-xxx" not in block.content


def test_message_metadata_excludes_full_drafts(
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
    assert "technical_task_draft" not in metadata
    assert "visual_brief" not in metadata
    assert metadata.get("block_types") == ["draft"]
    assert "deliverables" not in json.dumps(metadata).lower()


def test_preview_uses_readable_assistant_content() -> None:
    from app.db.models.agent_chat import AgentChatMessageTable
    from app.schemas.contracts import AgentChatMessageRole

    sample = _sample_technical_task_draft()
    sample["summary"] = "Bot"
    sample["assistant_excerpt"] = "Use webhooks."
    summary = format_technical_task_summary(sample)
    message = AgentChatMessageTable(
        session_id=uuid4(),
        role=AgentChatMessageRole.ASSISTANT,
        content=summary,
        message_metadata={"block_types": ["draft"], "domain": "programmer"},
    )
    preview = build_preview_from_message(message)
    assert preview is not None
    assert "{" not in preview
    assert "technical_task_draft" not in preview.lower()


def test_preview_max_length_enforced() -> None:
    preview = build_message_preview("x" * 300)
    assert preview is not None
    assert len(preview) <= 164


def test_direct_programmer_clarification_block(
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
    assert body["blocks"][0]["type"] == "clarification"
    assert body["blocks"][0]["domain"] == "programmer"
    assert PROGRAMMER_DIRECT_CLARIFICATION in body["blocks"][0]["content"]


def test_api_response_includes_output_and_blocks(
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
    assert "output" in body
    assert "blocks" in body
    assert body["session_id"]
    assert body["assistant_message_id"] == body["assistant_message"]["id"]
