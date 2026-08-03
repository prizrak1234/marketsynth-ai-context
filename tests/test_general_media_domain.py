"""Phase AI.17 — General → Media domain skeleton."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from app.agents.general.contracts import GeneralDomain
from app.agents.general.execution import GENERAL_DELEGATION_SOURCE
from app.agents.general.prompts import UNKNOWN_DOMAIN_CLARIFICATION
from app.agents.general.router import detect_general_domain
from app.agents.media.contracts import MEDIA_FORBIDDEN_TOOL_MARKERS
from app.agents.media.execution import build_visual_brief, infer_visual_format
from app.agents.run_depth import compute_agent_run_depth
from app.core.exceptions import InvalidStateError
from app.schemas.contracts import AgentType
from app.services.agent_runs import AgentRunService
from app.tools.agent_tool_profiles import DEFAULT_AGENT_TOOL_ALLOWLIST, get_agent_tool_allowlist
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient

MEDIA_DIR = Path(__file__).resolve().parents[1] / "app" / "agents" / "media"

LAUNCH_MESSAGE = "Запусти новый продукт"
UNKNOWN_MESSAGE = "Как настроить PostgreSQL replication?"
TELEGRAM_BOT_MESSAGE = "Сделай telegram bot для уведомлений"
TELEGRAM_POST_MESSAGE = "Напиши пост в telegram"
BANNER_TELEGRAM_MESSAGE = "Сделай баннер для telegram канала"
CREATIVE_MESSAGE = "Придумай креатив для stories"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Media Domain"}, headers=headers)
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


def test_detect_media_domain_phrases() -> None:
    assert detect_general_domain(message=BANNER_TELEGRAM_MESSAGE) == GeneralDomain.MEDIA
    assert detect_general_domain(message=CREATIVE_MESSAGE) == GeneralDomain.MEDIA
    assert detect_general_domain(message="Нужен визуал для баннера") == GeneralDomain.MEDIA


def test_banner_for_telegram_is_media_not_marketing() -> None:
    assert detect_general_domain(message=BANNER_TELEGRAM_MESSAGE) == GeneralDomain.MEDIA
    assert detect_general_domain(message="Баннер в telegram") == GeneralDomain.MEDIA


def test_telegram_bot_still_programmer() -> None:
    assert detect_general_domain(message=TELEGRAM_BOT_MESSAGE) == GeneralDomain.PROGRAMMER


def test_telegram_post_still_marketing() -> None:
    assert detect_general_domain(message=TELEGRAM_POST_MESSAGE) == GeneralDomain.MARKETING
    assert detect_general_domain(message="Контент для telegram кампании") == GeneralDomain.MARKETING


def test_marketing_launch_unchanged() -> None:
    assert detect_general_domain(message=LAUNCH_MESSAGE) == GeneralDomain.MARKETING


def test_unknown_unchanged() -> None:
    assert detect_general_domain(message=UNKNOWN_MESSAGE) == GeneralDomain.UNKNOWN


def test_media_tool_profile_empty() -> None:
    assert DEFAULT_AGENT_TOOL_ALLOWLIST[AgentType.MEDIA] == frozenset()
    assert get_agent_tool_allowlist(AgentType.MEDIA) == frozenset()


def test_media_no_image_video_canva_figma_heygen_tools() -> None:
    allowlist = get_agent_tool_allowlist(AgentType.MEDIA)
    registered = {tool.name.lower() for tool in get_tool_registry().list_registered()}
    for name in registered:
        for marker in MEDIA_FORBIDDEN_TOOL_MARKERS:
            assert marker not in name
    assert allowlist.isdisjoint(registered)


def test_media_execution_module_no_generation_integrations() -> None:
    source = (MEDIA_DIR / "execution.py").read_text(encoding="utf-8").lower()
    for marker in ("canva", "heygen", "openai.images", "image.generate", "httpx", "upload"):
        assert marker not in source


def test_visual_brief_persisted_false() -> None:
    brief = build_visual_brief(message=BANNER_TELEGRAM_MESSAGE, assistant_excerpt="Mock")
    assert brief["persisted"] is False
    assert brief["format"] == "telegram_banner"


def test_infer_visual_format_telegram_banner() -> None:
    assert infer_visual_format(message=BANNER_TELEGRAM_MESSAGE) == "telegram_banner"


def test_unknown_no_delegation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": UNKNOWN_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    assert body.get("general_delegation") is None
    assert UNKNOWN_DOMAIN_CLARIFICATION in body["assistant_message"]["content"]


def test_media_delegation_with_visual_brief(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    media_id = _create_agent(client, auth_headers, project_id, agent_type="media")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": BANNER_TELEGRAM_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    )
    assert sent.status_code == 200
    body = sent.json()
    delegation = body["general_delegation"]
    assert delegation["domain"] == "media"

    general_run = client.get(f"/agent-runs/{body['agent_run_id']}", headers=auth_headers).json()
    media_run = client.get(
        f"/agent-runs/{delegation['agent_run_id']}",
        headers=auth_headers,
    ).json()

    assert general_run["parent_agent_run_id"] is None
    assert media_run["parent_agent_run_id"] == body["agent_run_id"]
    assert media_run["agent_id"] == media_id
    assert media_run["input_payload"]["delegated_domain"] == "media"
    assert media_run["input_payload"]["source"] == GENERAL_DELEGATION_SOURCE
    assert body.get("subagent_chain") is None

    brief = (media_run.get("output_payload") or {}).get("visual_brief")
    assert brief is not None
    assert brief["persisted"] is False
    assert brief["format"] == "telegram_banner"
    assert brief.get("concept")
    assert brief.get("composition")


@pytest.mark.asyncio
async def test_media_child_depth_one_no_children(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    _create_agent(client, auth_headers, project_id, agent_type="media")

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": CREATIVE_MESSAGE, "agent_id": general_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    agent_runs = AgentRunService(db_session)

    general_run = await agent_runs.get_run(owner_id, UUID(sent["agent_run_id"]))
    media_run = await agent_runs.get_run(
        owner_id,
        UUID(sent["general_delegation"]["agent_run_id"]),
    )
    assert general_run is not None
    assert media_run is not None
    assert await compute_agent_run_depth(db_session, general_run, owner_id) == 0
    assert await compute_agent_run_depth(db_session, media_run, owner_id) == 1
    assert await agent_runs.count_children(media_run.id, owner_id) == 0


@pytest.mark.asyncio
async def test_media_child_cannot_spawn_children(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    project_id = _create_project(client, auth_headers)
    general_id = _create_agent(client, auth_headers, project_id, agent_type="general")
    media_agent_id = UUID(_create_agent(client, auth_headers, project_id, agent_type="media"))

    sent = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": "Сделай обложку для видео", "agent_id": general_id},
        headers=auth_headers,
    ).json()
    owner_id = UUID(sent["session"]["owner_id"])
    media_run = await AgentRunService(db_session).get_run(
        owner_id,
        UUID(sent["general_delegation"]["agent_run_id"]),
    )
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
