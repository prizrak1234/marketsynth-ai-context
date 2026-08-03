"""Phase AI.25 — Chat observability + audit metrics."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_audit_event import ChatAuditEventTable
from app.schemas.contracts import ChatAuditEventType, ChatBlockActionType
from app.services.chat_audit_safe_metadata import build_safe_metadata
from app.services.chat_audit_service import ChatAuditService

PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"
SECRET_PHRASE = "super-secret-api-key-do-not-log"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Chat Observability"}, headers=headers)
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


def _audit_events(
    db_session: AsyncSession,
    project_id: str,
    *,
    event_type: str | None = None,
) -> list[ChatAuditEventTable]:
    statement = select(ChatAuditEventTable).where(
        ChatAuditEventTable.project_id == UUID(project_id),
    )
    if event_type is not None:
        statement = statement.where(ChatAuditEventTable.event_type == event_type)
    result = db_session.execute(statement)
    return list(result.scalars().all())


def test_safe_metadata_strips_forbidden_fields() -> None:
    safe = build_safe_metadata(
        {
            "content_length": 42,
            "query": "must not appear",
            "content": "secret body",
            "output_payload": {"x": 1},
            "block_types": ["draft"],
        },
    )
    assert safe.get("content_length") == 42
    assert "query" not in safe
    assert "content" not in safe
    assert "output_payload" not in safe
    assert safe.get("block_types") == ["draft"]


def test_session_create_emits_safe_audit_event(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()

    events = _audit_events(db_session, project_id, event_type=ChatAuditEventType.SESSION_CREATED)
    assert len(events) >= 1
    event = events[0]
    assert event.session_id == UUID(body["session_id"])
    blob = json.dumps(event.safe_metadata).lower()
    assert PROGRAMMER_MSG not in blob
    assert "content" not in blob


def test_message_append_audit_has_length_not_content(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    )

    user_events = _audit_events(
        db_session,
        project_id,
        event_type=ChatAuditEventType.MESSAGE_USER_APPENDED,
    )
    assert user_events
    assert user_events[0].safe_metadata.get("content_length", 0) > 0
    assert "content" not in user_events[0].safe_metadata


def test_run_lifecycle_audit_events(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    )

    started = _audit_events(db_session, project_id, event_type=ChatAuditEventType.RUN_STARTED)
    succeeded = _audit_events(db_session, project_id, event_type=ChatAuditEventType.RUN_SUCCEEDED)
    assert started
    assert succeeded
    assert "agent_run_id" in started[0].safe_metadata
    assert "output_payload" not in json.dumps(succeeded[0].safe_metadata).lower()


def test_block_action_audit_events(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.COPY_TEXT.value,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    requested = _audit_events(
        db_session,
        project_id,
        event_type=ChatAuditEventType.BLOCK_ACTION_REQUESTED,
    )
    succeeded = _audit_events(
        db_session,
        project_id,
        event_type=ChatAuditEventType.BLOCK_ACTION_SUCCEEDED,
    )
    assert requested
    assert succeeded
    assert requested[0].safe_metadata.get("action_type") == ChatBlockActionType.COPY_TEXT.value
    assert "text" not in json.dumps(succeeded[0].safe_metadata).lower()


def test_failed_block_action_emits_safe_error(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.CREATE_MARKETING_ASSET.value,
        },
        headers=auth_headers,
    )
    assert response.status_code == 409

    failed = _audit_events(
        db_session,
        project_id,
        event_type=ChatAuditEventType.BLOCK_ACTION_FAILED,
    )
    assert failed
    meta = failed[0].safe_metadata
    assert meta.get("safe_message")
    assert meta.get("error_code")
    assert "output_payload" not in json.dumps(meta).lower()


def test_search_emits_query_length_not_query_text(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    unique = "ObservabilitySearchMarker"
    client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": unique, "agent_id": programmer_id},
        headers=auth_headers,
    )

    client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": "ObservabilitySearch", "agent_id": programmer_id},
        headers=auth_headers,
    )

    events = _audit_events(db_session, project_id, event_type=ChatAuditEventType.SEARCH_MESSAGES)
    assert events
    meta = events[-1].safe_metadata
    assert meta.get("query_length", 0) > 0
    assert "query" not in meta
    assert unique not in json.dumps(meta)


def test_metrics_endpoint_counts_activity(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
        headers=auth_headers,
    )
    client.get(
        f"/projects/{project_id}/agent-chat/search-messages",
        params={"query": "webhook", "agent_id": programmer_id},
        headers=auth_headers,
    )

    metrics = client.get(
        f"/projects/{project_id}/agent-chat/metrics",
        headers=auth_headers,
    )
    assert metrics.status_code == 200
    data = metrics.json()
    assert data["sessions_total"] >= 1
    assert data["messages_total"] >= 2
    assert data["messages_user"] >= 1
    assert data["messages_assistant"] >= 1
    assert data["runs_total"] >= 1
    assert data["searches_total"] >= 1
    assert data["searches_by_type"]["messages"] >= 1


def test_audit_events_endpoint_filters(
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

    all_events = client.get(
        f"/projects/{project_id}/agent-chat/audit-events",
        headers=auth_headers,
    )
    assert all_events.status_code == 200
    assert len(all_events.json()) >= 1

    filtered = client.get(
        f"/projects/{project_id}/agent-chat/audit-events",
        params={
            "session_id": chat["session_id"],
            "event_type": ChatAuditEventType.MESSAGE_USER_APPENDED.value,
        },
        headers=auth_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()
    assert all(item["session_id"] == chat["session_id"] for item in filtered.json())
    assert all(
        item["event_type"] == ChatAuditEventType.MESSAGE_USER_APPENDED.value
        for item in filtered.json()
    )


def test_audit_limit_max_enforced(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    response = client.get(
        f"/projects/{project_id}/agent-chat/audit-events",
        params={"limit": 500},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_audit_failure_does_not_break_chat_flow(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    with patch.object(ChatAuditService, "record", new_callable=AsyncMock) as mock_record:
        mock_record.side_effect = RuntimeError("audit storage unavailable")
        response = client.post(
            f"/projects/{project_id}/agent-chat",
            json={"content": PROGRAMMER_MSG, "agent_id": programmer_id},
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert response.json()["assistant_message"]["content"]
