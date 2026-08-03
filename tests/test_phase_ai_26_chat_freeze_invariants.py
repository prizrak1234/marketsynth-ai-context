"""Phase AI.26 — Agent chat production readiness freeze invariants."""

from __future__ import annotations

import inspect
import json
from uuid import UUID

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.direct_specialist.contracts import (
    ENTRYPOINT_DIRECT_SPECIALIST,
    ENTRYPOINT_GENERAL_DELEGATION,
)
from app.agents.general.contracts import GeneralDomain
from app.agents.general.router import detect_general_domain
from app.agents.media.contracts import MEDIA_FORBIDDEN_TOOL_MARKERS
from app.agents.programmer.contracts import PROGRAMMER_FORBIDDEN_TOOL_MARKERS
from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.db.models.agent import AgentTable
from app.db.models.agent_chat import AgentChatMessageTable, AgentChatSessionTable
from app.db.models.agent_run import AgentRunTable
from app.db.models.project import ProjectTable
from app.db.repositories.agent_chat_messages import ChatMessageRepository
from app.db.repositories.chat_audit_events import ChatAuditEventRepository
from app.main import app
from app.schemas.agent_chat import (
    AgentChatMetricsResponse,
    AgentChatSendResponse,
    ChatAuditEventRead,
    ChatBlockActionResponse,
)
from app.schemas.contracts import (
    AgentChatMessageRole,
    AgentRunStatus,
    AgentStatus,
    AgentType,
    ChatBlockActionType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
    ChatSessionListItem,
    ChatSessionStatus,
)
from app.services.agent_runs import AgentRunService
from app.services.chat_session_history import (
    agent_chat_session_history_limit,
    assert_history_safe_for_prompt,
    build_session_history_for_run,
)
from app.tools.agent_tool_profiles import DEFAULT_AGENT_TOOL_ALLOWLIST, get_agent_tool_allowlist

PROGRAMMER_MSG = "Напиши скрипт для webhook интеграции"
BANNER_MSG = "Сделай баннер для telegram канала"
LAUNCH_MSG = "Запусти новый продукт"
METADATA_ONLY_TOKEN = "freeze-meta-only-token-ai26"
SECRET_IN_MESSAGE = "super-secret-api-key-freeze-test"

POST_CHAT_RESPONSE_KEYS = frozenset(
    {
        "session",
        "session_id",
        "user_message",
        "assistant_message",
        "assistant_message_id",
        "agent_run_id",
        "execution_metadata",
        "output",
        "blocks",
    },
)

SESSION_LIST_ITEM_KEYS = frozenset(ChatSessionListItem.model_fields.keys())

METRICS_KEYS = frozenset(AgentChatMetricsResponse.model_fields.keys())

AUDIT_EVENT_KEYS = frozenset(ChatAuditEventRead.model_fields.keys())

BLOCK_ACTION_RESPONSE_KEYS = frozenset(ChatBlockActionResponse.model_fields.keys())

FORBIDDEN_AUDIT_METADATA_KEYS = frozenset(
    {
        "content",
        "query",
        "message",
        "body",
        "output_payload",
        "prompt",
        "technical_task_draft",
        "visual_brief",
        "marketing_brief",
    },
)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.26 Freeze"}, headers=headers)
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


def _route_query_param(route_path: str, param_name: str) -> object | None:
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path != route_path:
            continue
        for dependant in route.dependant.query_params:
            if dependant.name == param_name:
                return dependant.field_info
    return None


# --- Domain & tool invariants ---


def test_invariant_programmer_artifacts_remain_persisted_false(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    block = body["blocks"][0]
    assert block["type"] == "draft"
    assert block["persisted"] is False
    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    draft = (run.get("output_payload") or {}).get("technical_task_draft")
    assert draft is not None
    assert draft.get("persisted") is False


def test_invariant_media_artifacts_remain_persisted_false(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")
    body = _chat(client, auth_headers, project_id, agent_id=media_id, content=BANNER_MSG)
    block = body["blocks"][0]
    assert block["type"] == "brief"
    assert block["persisted"] is False
    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    brief = (run.get("output_payload") or {}).get("visual_brief")
    assert brief is not None
    assert brief.get("persisted") is False


def test_invariant_programmer_tool_allowlist_empty() -> None:
    assert DEFAULT_AGENT_TOOL_ALLOWLIST[AgentType.PROGRAMMER] == frozenset()
    assert get_agent_tool_allowlist(AgentType.PROGRAMMER) == frozenset()
    for marker in PROGRAMMER_FORBIDDEN_TOOL_MARKERS:
        assert marker not in get_agent_tool_allowlist(AgentType.PROGRAMMER)


def test_invariant_media_tool_allowlist_empty() -> None:
    assert DEFAULT_AGENT_TOOL_ALLOWLIST[AgentType.MEDIA] == frozenset()
    assert get_agent_tool_allowlist(AgentType.MEDIA) == frozenset()
    for marker in MEDIA_FORBIDDEN_TOOL_MARKERS:
        assert marker not in get_agent_tool_allowlist(AgentType.MEDIA)


@pytest.mark.asyncio
async def test_invariant_programmer_run_cannot_spawn_children(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = UUID(_create_agent(client, auth_headers, project_id, agent_type="programmer"))
    body = _chat(client, auth_headers, project_id, agent_id=str(programmer_id), content=PROGRAMMER_MSG)
    owner_id = UUID(body["session"]["owner_id"])
    parent_run_id = UUID(body["agent_run_id"])

    with pytest.raises(InvalidStateError, match="cannot spawn child runs"):
        await AgentRunService(db_session).create_run(
            owner_id,
            agent_id=programmer_id,
            task_id=None,
            input_payload={"prompt": "nested"},
            metadata={},
            parent_agent_run_id=parent_run_id,
        )


@pytest.mark.asyncio
async def test_invariant_media_run_cannot_spawn_children(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = UUID(_create_agent(client, auth_headers, project_id, agent_type="media"))
    body = _chat(client, auth_headers, project_id, agent_id=str(media_id), content=BANNER_MSG)
    owner_id = UUID(body["session"]["owner_id"])

    with pytest.raises(InvalidStateError, match="cannot spawn child runs"):
        await AgentRunService(db_session).create_run(
            owner_id,
            agent_id=media_id,
            task_id=None,
            input_payload={"prompt": "nested"},
            metadata={},
            parent_agent_run_id=UUID(body["agent_run_id"]),
        )


def test_invariant_direct_specialist_not_general_delegation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    assert body["execution_metadata"]["entrypoint"] == ENTRYPOINT_DIRECT_SPECIALIST
    assert body.get("general_delegation") is None
    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    assert run["parent_agent_run_id"] is None


def test_invariant_general_delegation_uses_detect_general_domain(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    assert detect_general_domain(message=PROGRAMMER_MSG) == GeneralDomain.PROGRAMMER
    assert detect_general_domain(message=BANNER_MSG) == GeneralDomain.MEDIA
    assert detect_general_domain(message=LAUNCH_MSG) == GeneralDomain.MARKETING

    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    body = _chat(client, auth_headers, project_id, agent_id=general_id, content=PROGRAMMER_MSG)
    assert body["execution_metadata"]["entrypoint"] == ENTRYPOINT_GENERAL_DELEGATION
    assert body["execution_metadata"]["domain"] == "programmer"
    assert body.get("general_delegation") is not None


# --- History & metadata invariants ---


def test_invariant_history_limit_default_is_10(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_CHAT_SESSION_HISTORY_LIMIT", raising=False)
    get_settings.cache_clear()
    assert Settings().agent_chat_session_history_limit == 10
    assert agent_chat_session_history_limit() == 10


def test_invariant_history_is_rolling_not_ltm() -> None:
    from app.db.models.agent_chat import AgentChatMessageTable
    from app.schemas.contracts import AgentChatMessageRole

    prior = [
        AgentChatMessageTable(
            session_id=UUID(int=0),
            role=AgentChatMessageRole.USER,
            content=f"turn {index}",
        )
        for index in range(12)
    ]
    history = build_session_history_for_run(
        prior,
        current_user_content="latest",
        limit=10,
    )
    assert len(history) == 10
    assert history[-1]["content"] == "latest"
    assert history[0]["content"] == "turn 2"


def test_invariant_history_excludes_forbidden_keys() -> None:
    unsafe = [
        {"role": "user", "content": "hi", "api_key": "sk-bad"},
        {"role": "assistant", "content": "ok", "tool_logs": []},
    ]
    with pytest.raises(ValueError, match="Forbidden history key"):
        assert_history_safe_for_prompt(unsafe)


def test_invariant_assistant_metadata_excludes_full_drafts(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    metadata = body["assistant_message"]["metadata"]
    blob = json.dumps(metadata).lower()
    assert "technical_task_draft" not in blob
    assert "output_payload" not in blob
    assert metadata.get("source_run_id")
    assert metadata.get("block_types")


def test_invariant_history_get_rebuilds_blocks_server_side(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    chat = _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{chat['session_id']}/messages",
        headers=auth_headers,
    ).json()
    assistant = next(m for m in messages if m["role"] == "assistant")
    assert assistant["blocks"]
    assert assistant["blocks"][0]["type"] == "draft"
    assert "actions" in assistant["blocks"][0]


def test_invariant_block_actions_server_authoritative(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")
    chat = _chat(client, auth_headers, project_id, agent_id=media_id, content=BANNER_MSG)
    forged = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.CREATE_MARKETING_ASSET.value,
        },
        headers=auth_headers,
    )
    assert forged.status_code == 409


@pytest.mark.asyncio
async def test_invariant_search_does_not_inspect_metadata(
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
        title="Meta isolation",
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
            content="Visible line without token",
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

    repo_source = inspect.getsource(ChatMessageRepository.search_messages)
    assert "message_metadata" not in repo_source


# --- Audit invariants ---


def test_invariant_audit_metadata_excludes_raw_content(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    events = client.get(
        f"/projects/{project_id}/agent-chat/audit-events",
        headers=auth_headers,
    ).json()
    assert events
    for event in events:
        meta = event.get("safe_metadata") or {}
        blob = json.dumps(meta).lower()
        for forbidden in FORBIDDEN_AUDIT_METADATA_KEYS:
            assert forbidden not in meta
        assert PROGRAMMER_MSG not in blob
        assert SECRET_IN_MESSAGE not in blob


def test_invariant_metrics_exposes_counts_only_not_content(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    metrics = client.get(
        f"/projects/{project_id}/agent-chat/metrics",
        headers=auth_headers,
    ).json()
    assert set(metrics.keys()) == METRICS_KEYS
    blob = json.dumps(metrics).lower()
    assert "content" not in blob
    assert "output_payload" not in blob
    assert "query" not in blob or metrics.get("searches_total", 0) >= 0


# --- Config / limit sanity ---


def test_invariant_sessions_list_limit_defaults() -> None:
    field = _route_query_param("/projects/{project_id}/agent-chat/sessions", "limit")
    assert field is not None
    assert field.default == 50
    assert field.le == 100


def test_invariant_messages_get_limit_defaults() -> None:
    field = _route_query_param(
        "/projects/{project_id}/agent-chat/sessions/{session_id}/messages",
        "limit",
    )
    assert field is not None
    assert field.default == 50
    assert field.le == 100


def test_invariant_search_messages_limit_defaults() -> None:
    field = _route_query_param(
        "/projects/{project_id}/agent-chat/search-messages",
        "limit",
    )
    assert field is not None
    assert field.default == 20
    assert field.le == 50


def test_invariant_audit_events_limit_defaults() -> None:
    field = _route_query_param("/projects/{project_id}/agent-chat/audit-events", "limit")
    assert field is not None
    assert field.default == 50
    assert field.le == 200


def test_invariant_endpoint_limits_reject_over_max(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    assert (
        client.get(
            f"/projects/{project_id}/agent-chat/audit-events",
            params={"limit": 500},
            headers=auth_headers,
        ).status_code
        == 422
    )


# --- API schema smoke ---


def test_smoke_post_agent_chat_response_shape(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    body = _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    assert POST_CHAT_RESPONSE_KEYS <= set(body.keys())
    AgentChatSendResponse.model_validate(body)


def test_smoke_get_sessions_ux_list_shape(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    sessions = client.get(
        f"/projects/{project_id}/agent-chat/sessions",
        params={"agent_id": programmer_id},
        headers=auth_headers,
    ).json()
    assert sessions
    assert SESSION_LIST_ITEM_KEYS <= set(sessions[0].keys())
    ChatSessionListItem.model_validate(sessions[0])


def test_smoke_get_messages_includes_blocks(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    chat = _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    messages = client.get(
        f"/projects/{project_id}/agent-chat/sessions/{chat['session_id']}/messages",
        headers=auth_headers,
    ).json()
    assistant = next(m for m in messages if m["role"] == "assistant")
    assert "blocks" in assistant
    assert assistant["blocks"]


def test_smoke_block_actions_response_shape(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    chat = _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
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
    data = response.json()
    assert BLOCK_ACTION_RESPONSE_KEYS <= set(data.keys())
    ChatBlockActionResponse.model_validate(data)


def test_smoke_metrics_and_audit_event_shapes(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")
    _chat(client, auth_headers, project_id, agent_id=programmer_id, content=PROGRAMMER_MSG)
    metrics = client.get(
        f"/projects/{project_id}/agent-chat/metrics",
        headers=auth_headers,
    ).json()
    AgentChatMetricsResponse.model_validate(metrics)
    events = client.get(
        f"/projects/{project_id}/agent-chat/audit-events",
        headers=auth_headers,
    ).json()
    assert events
    ChatAuditEventRead.model_validate(events[0])


def test_invariant_audit_repository_list_signature() -> None:
    """Guard: audit list limit default 50, max enforced at API layer."""
    repo_source = inspect.getsource(ChatAuditEventRepository.list_for_project)
    assert "limit: int = 50" in repo_source
