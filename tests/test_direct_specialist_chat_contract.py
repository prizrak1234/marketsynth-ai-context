"""Phase AI.18 — Direct specialist chat contract."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.agents.direct_specialist.contracts import (
    ENTRYPOINT_DIRECT_SPECIALIST,
    ENTRYPOINT_GENERAL_DELEGATION,
)
from app.agents.direct_specialist.prompts import (
    MEDIA_DIRECT_CLARIFICATION,
    PROGRAMMER_DIRECT_CLARIFICATION,
)
from app.agents.general.execution import GENERAL_DELEGATION_SOURCE
from app.agents.general.prompts import UNKNOWN_DOMAIN_CLARIFICATION
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import AgentType
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from fastapi.testclient import TestClient

PROGRAMMER_SCRIPT_MESSAGE = "Напиши скрипт для webhook интеграции"
PROGRAMMER_BOT_MESSAGE = "Сделай telegram bot для уведомлений"
BANNER_TELEGRAM_MESSAGE = "Сделай баннер для telegram канала"
TELEGRAM_POST_MESSAGE = "Напиши пост в telegram"
LAUNCH_MESSAGE = "Запусти новый продукт"
UNKNOWN_MESSAGE = "Как настроить PostgreSQL replication?"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Direct Specialist"}, headers=headers)
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


def _send(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_id: str,
    content: str,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": content, "agent_id": agent_id},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_direct_programmer_returns_technical_task_draft_not_persisted(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_SCRIPT_MESSAGE,
    )
    meta = body["execution_metadata"]
    assert meta["entrypoint"] == ENTRYPOINT_DIRECT_SPECIALIST
    assert meta["domain"] == "programmer"
    assert body.get("general_delegation") is None

    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    assert run["parent_agent_run_id"] is None
    draft = (run.get("output_payload") or {}).get("technical_task_draft")
    assert draft is not None
    assert draft["persisted"] is False


def test_direct_media_returns_visual_brief_not_persisted(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=media_id,
        content=BANNER_TELEGRAM_MESSAGE,
    )
    meta = body["execution_metadata"]
    assert meta["entrypoint"] == ENTRYPOINT_DIRECT_SPECIALIST
    assert meta["domain"] == "media"

    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    brief = (run.get("output_payload") or {}).get("visual_brief")
    assert brief is not None
    assert brief["persisted"] is False
    assert brief.get("format") == "telegram_banner"


def test_direct_media_telegram_banner_does_not_route_to_marketing(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=media_id,
        content=BANNER_TELEGRAM_MESSAGE,
    )
    assert body["execution_metadata"]["domain"] == "media"
    assert body.get("subagent_chain") is None
    assert body.get("general_delegation") is None


def test_direct_programmer_telegram_bot_does_not_route_to_media_or_marketing(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=PROGRAMMER_BOT_MESSAGE,
    )
    assert body["execution_metadata"]["domain"] == "programmer"
    assert body.get("general_delegation") is None
    assert body.get("subagent_chain") is None


def test_direct_programmer_off_topic_clarification_not_general(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_id = _create_agent(client, auth_headers, project_id, agent_type="programmer")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=programmer_id,
        content=BANNER_TELEGRAM_MESSAGE,
    )
    assert PROGRAMMER_DIRECT_CLARIFICATION in body["assistant_message"]["content"]
    assert UNKNOWN_DOMAIN_CLARIFICATION not in body["assistant_message"]["content"]
    assert body["execution_metadata"]["entrypoint"] == ENTRYPOINT_DIRECT_SPECIALIST
    assert body["execution_metadata"]["domain"] == "programmer"


def test_direct_media_off_topic_clarification_not_general(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=media_id,
        content=PROGRAMMER_BOT_MESSAGE,
    )
    assert MEDIA_DIRECT_CLARIFICATION in body["assistant_message"]["content"]
    assert UNKNOWN_DOMAIN_CLARIFICATION not in body["assistant_message"]["content"]
    assert body["execution_metadata"]["domain"] == "media"


@pytest.mark.asyncio
async def test_no_child_spawn_under_programmer_direct(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    programmer_agent_id = UUID(
        _create_agent(client, auth_headers, project_id, agent_type="programmer"),
    )
    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=str(programmer_agent_id),
        content=PROGRAMMER_SCRIPT_MESSAGE,
    )
    owner_id = UUID(body["session"]["owner_id"])
    programmer_run = await AgentRunService(db_session).get_run(
        owner_id,
        UUID(body["agent_run_id"]),
    )
    assert programmer_run is not None
    assert programmer_run.parent_agent_run_id is None

    with pytest.raises(InvalidStateError, match="cannot spawn child runs"):
        await AgentRunService(db_session).create_run(
            owner_id,
            agent_id=programmer_agent_id,
            task_id=programmer_run.task_id,
            input_payload={"prompt": "nested"},
            metadata={},
            parent_agent_run_id=programmer_run.id,
        )


@pytest.mark.asyncio
async def test_no_child_spawn_under_media_direct(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    media_agent_id = UUID(_create_agent(client, auth_headers, project_id, agent_type="media"))
    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=str(media_agent_id),
        content=BANNER_TELEGRAM_MESSAGE,
    )
    owner_id = UUID(body["session"]["owner_id"])
    media_run = await AgentRunService(db_session).get_run(owner_id, UUID(body["agent_run_id"]))
    assert media_run is not None

    with pytest.raises(InvalidStateError, match="cannot spawn child runs"):
        await AgentRunService(db_session).create_run(
            owner_id,
            agent_id=media_agent_id,
            task_id=media_run.task_id,
            input_payload={"prompt": "nested"},
            metadata={},
            parent_agent_run_id=media_run.id,
        )


def test_empty_tool_allowlists_programmer_media_direct() -> None:
    assert get_agent_tool_allowlist(AgentType.PROGRAMMER) == frozenset()
    assert get_agent_tool_allowlist(AgentType.MEDIA) == frozenset()


def test_general_delegation_entrypoint_unchanged(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="programmer")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=general_id,
        content=PROGRAMMER_SCRIPT_MESSAGE,
    )
    assert body["execution_metadata"]["entrypoint"] == ENTRYPOINT_GENERAL_DELEGATION
    assert body["execution_metadata"]["domain"] == "programmer"
    assert body["general_delegation"]["domain"] == "programmer"

    child_run = client.get(
        f"/agent-runs/{body['general_delegation']['agent_run_id']}",
        headers=auth_headers,
    ).json()
    assert child_run["input_payload"]["source"] == GENERAL_DELEGATION_SOURCE
    assert child_run["metadata"]["execution_metadata"]["entrypoint"] == (
        ENTRYPOINT_GENERAL_DELEGATION
    )


def test_direct_marketing_orchestrator_entrypoint(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=orchestrator_id,
        content=TELEGRAM_POST_MESSAGE,
    )
    assert body["execution_metadata"]["entrypoint"] == ENTRYPOINT_DIRECT_SPECIALIST
    assert body["execution_metadata"]["domain"] == "marketing"
    assert body.get("general_delegation") is None


def test_direct_run_metadata_stamped_on_create(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=media_id,
        content=BANNER_TELEGRAM_MESSAGE,
    )
    run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    assert run["metadata"]["execution_metadata"] == {
        "entrypoint": ENTRYPOINT_DIRECT_SPECIALIST,
        "domain": "media",
    }


def test_general_unknown_still_general_delegation_entrypoint(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=general_id,
        content=UNKNOWN_MESSAGE,
    )
    assert body["execution_metadata"]["entrypoint"] == ENTRYPOINT_GENERAL_DELEGATION
    assert body["execution_metadata"]["domain"] == "unknown"
    assert body.get("general_delegation") is None


def test_general_marketing_delegation_regression(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    _create_agent(client, auth_headers, project_id, agent_type="researcher")
    _create_agent(client, auth_headers, project_id, agent_type="strategist")
    _create_agent(client, auth_headers, project_id, agent_type="copywriter")

    body = _send(
        client,
        auth_headers,
        project_id,
        agent_id=general_id,
        content=LAUNCH_MESSAGE,
    )
    assert body["general_delegation"]["domain"] == "marketing"
    assert body["execution_metadata"]["entrypoint"] == ENTRYPOINT_GENERAL_DELEGATION
