"""Agent registry API tests."""

from __future__ import annotations

import pytest
from app.db.repositories.agent_repo import AgentRepository
from app.schemas.contracts import AgentStatus, AgentType
from app.services.agents import AgentService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _create_project(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Agent Project",
) -> str:
    response = client.post("/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_create_agent_in_own_project(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["type"] == "strategist"
    assert body["status"] == "draft"
    assert body["name"] == "Strategist"
    assert len(body["capabilities"]) >= 1


def test_cannot_create_agent_in_foreign_project(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers, name="Private project")
    response = client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_list_agents_only_shows_current_user(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    own_project = _create_project(client, auth_headers, name="Own")
    other_project = _create_project(client, other_auth_headers, name="Other")

    own_agent = client.post(
        "/agents",
        json={"project_id": own_project, "type": "copywriter"},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        "/agents",
        json={"project_id": other_project, "type": "critic"},
        headers=other_auth_headers,
    )

    listed = client.get("/agents", headers=auth_headers)
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert own_agent in ids
    assert len(ids) == 1


def test_activate_and_pause_change_status(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "analyst"},
        headers=auth_headers,
    ).json()["id"]

    activated = client.post(f"/agents/{agent_id}/activate", headers=auth_headers)
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"

    paused = client.post(f"/agents/{agent_id}/pause", headers=auth_headers)
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"


def test_delete_archives_agent(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "content_planner"},
        headers=auth_headers,
    ).json()["id"]

    deleted = client.delete(f"/agents/{agent_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "archived"

    listed = client.get("/agents", headers=auth_headers)
    assert all(item["id"] != agent_id for item in listed.json())

    archived_list = client.get("/agents", params={"include_archived": True}, headers=auth_headers)
    assert any(item["id"] == agent_id for item in archived_list.json())


@pytest.mark.asyncio
async def test_archived_agent_remains_in_database(db_session: AsyncSession) -> None:
    from app.schemas.crud import AgentCreateRequest, ProjectCreate, UserCreate
    from app.services.projects_service import ProjectService
    from app.services.users_service import UserService

    user = await UserService(db_session).create(UserCreate(telegram_id=91001))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=user.id, name="Archive test"),
    )
    service = AgentService(db_session)
    created = await service.create_agent(
        user.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.ORCHESTRATOR),
    )
    assert created is not None
    archived = await service.archive_agent(created.id, user.id)
    assert archived is not None
    assert archived.status == AgentStatus.ARCHIVED

    repo = AgentRepository(db_session)
    row = await repo.get_by_id(created.id)
    assert row is not None
    assert row.status == AgentStatus.ARCHIVED


def test_foreign_agent_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    agent_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "orchestrator"},
        headers=auth_headers,
    ).json()["id"]

    assert client.get(f"/agents/{agent_id}", headers=other_auth_headers).status_code == 404
    assert (
        client.patch(
            f"/agents/{agent_id}",
            json={"name": "Hacked"},
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert client.delete(f"/agents/{agent_id}", headers=other_auth_headers).status_code == 404


def test_default_agent_templates_cover_all_types() -> None:
    from app.agents.templates import DEFAULT_AGENT_TEMPLATES

    for agent_type in AgentType:
        assert agent_type in DEFAULT_AGENT_TEMPLATES
        template = DEFAULT_AGENT_TEMPLATES[agent_type]
        assert template["name"]
        assert template["description"]
        assert isinstance(template["default_config"], dict)
        assert len(template["capabilities"]) >= 1
