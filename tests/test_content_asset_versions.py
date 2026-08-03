"""Phase 4.4 — content asset versioning."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.content_asset_versions import ContentAssetVersionRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.contracts import ContentAssetType, ContentAssetVersionSource
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate, TaskCreate
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService
from app.services.content_asset_service import ContentAssetService
from app.services.projects_service import ProjectService
from app.services.tasks_service import TaskService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import (
    CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    CONTENT_ASSET_GET_TOOL_NAME,
)
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _tool_data(result) -> dict:
    assert result.output["ok"] is True
    return result.output["data"]


def _context(*, owner_id, project_id, agent_id, agent_run_id=None) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=agent_id,
        agent_type=AgentType.COPYWRITER,
        agent_run_id=agent_run_id or uuid4(),
        request_id=uuid4(),
    )


async def _seed_copywriter_with_run(db_session: AsyncSession, *, telegram_id: int):
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Versions {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.COPYWRITER),
    )
    assert agent is not None
    task = await TaskService(db_session).create(
        TaskCreate(
            project_id=project.id,
            agent_id=agent.id,
            title="Draft task",
        ),
    )
    assert task is not None
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=task.id,
        input_payload={"prompt": "draft"},
        metadata={},
    )
    assert run is not None
    return owner, project, agent, run


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Versioning"},
        headers=headers,
    ).json()["id"]


def _create_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Asset",
    body: str = "v1 body",
    metadata: dict | None = None,
) -> dict:
    payload: dict = {"type": "email", "title": title, "body": body}
    if metadata is not None:
        payload["metadata"] = metadata
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _versions(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
) -> list[dict]:
    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/versions",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_http_create_creates_version_1(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    assert asset["current_version_number"] == 1
    assert asset["approved_version_number"] is None

    versions = _versions(client, auth_headers, project_id, asset["id"])
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["body"] == "v1 body"
    assert versions[0]["created_by_source"] == "http_api"


@pytest.mark.asyncio
async def test_agent_create_draft_creates_version_1_with_agent_source(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()

    owner, project, agent, run = await _seed_copywriter_with_run(db_session, telegram_id=9801)
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_ca_version_agent",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "email",
                "title": "Agent draft",
                "body": "from agent",
            },
        ),
        _context(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    asset_id = UUID(_tool_data(result)["asset"]["id"])

    versions_repo = ContentAssetVersionRepository(db_session)
    versions = await versions_repo.list_versions(
        asset_id,
        owner.id,
        project.id,
    )
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].created_by_source == ContentAssetVersionSource.AGENT_TOOL
    assert versions[0].created_by_agent_run_id == run.id


def test_update_body_creates_version_2(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    updated = client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"body": "v2 body"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["current_version_number"] == 2
    versions = _versions(client, auth_headers, project_id, asset["id"])
    assert [v["version_number"] for v in versions] == [1, 2]
    assert versions[1]["body"] == "v2 body"


def test_update_title_creates_version_2(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id, title="Original")
    client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"title": "Renamed"},
        headers=auth_headers,
    )
    versions = _versions(client, auth_headers, project_id, asset["id"])
    assert len(versions) == 2
    assert versions[1]["title"] == "Renamed"


def test_update_metadata_creates_version_2(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id, metadata={"tone": "formal"})
    client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"metadata": {"tone": "casual"}},
        headers=auth_headers,
    )
    versions = _versions(client, auth_headers, project_id, asset["id"])
    assert len(versions) == 2
    assert versions[1]["metadata"]["tone"] == "casual"


def test_approve_does_not_create_new_version(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/approve",
        headers=auth_headers,
    )
    versions = _versions(client, auth_headers, project_id, asset["id"])
    assert len(versions) == 1


def test_approve_stores_approved_version_number(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"body": "final copy"},
        headers=auth_headers,
    )
    approved = client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/approve",
        headers=auth_headers,
    ).json()
    assert approved["current_version_number"] == 2
    assert approved["approved_version_number"] == 2


def test_archive_does_not_create_version(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/archive",
        headers=auth_headers,
    )
    assert len(_versions(client, auth_headers, project_id, asset["id"])) == 1


def test_approved_asset_content_update_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/approve",
        headers=auth_headers,
    )
    response = client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"body": "illegal edit"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_list_versions_ordered(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"body": "two"},
        headers=auth_headers,
    )
    client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"title": "three"},
        headers=auth_headers,
    )
    versions = _versions(client, auth_headers, project_id, asset["id"])
    numbers = [v["version_number"] for v in versions]
    assert numbers == [1, 2, 3]


def test_get_version_by_number(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id, body="first")
    client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"body": "second"},
        headers=auth_headers,
    )
    response = client.get(
        f"/projects/{project_id}/content-assets/{asset['id']}/versions/1",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["body"] == "first"
    assert response.json()["version_number"] == 1


def test_version_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset = _create_asset(client, auth_headers, project_id)
    denied = client.get(
        f"/projects/{project_id}/content-assets/{asset['id']}/versions",
        headers=other_auth_headers,
    )
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_content_asset_get_includes_version_fields(db_session: AsyncSession) -> None:
    owner, project, agent, _ = await _seed_copywriter_with_run(db_session, telegram_id=9802)
    row = await ContentAssetService(db_session).create(
        owner.id,
        project.id,
        asset_type=ContentAssetType.EMAIL,
        title="Tool read",
        body="hello",
    )
    assert row is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_ca_get_versions",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": str(row.id), "include_body": True},
        ),
        _context(owner_id=owner.id, project_id=project.id, agent_id=agent.id),
    )
    assert result.status == "succeeded"
    asset_payload = _tool_data(result)["asset"]
    assert asset_payload["current_version_number"] == 1
    assert asset_payload["approved_version_number"] is None
    assert asset_payload["body"] == "hello"


@pytest.mark.asyncio
async def test_existing_asset_has_version_1_after_service_create(
    db_session: AsyncSession,
) -> None:
    owner, project, _, _ = await _seed_copywriter_with_run(db_session, telegram_id=9803)
    assets = ContentAssetService(db_session)
    versions = ContentAssetVersionRepository(db_session)
    row = await assets.create(
        owner.id,
        project.id,
        asset_type=ContentAssetType.AD_COPY,
        title="Legacy shape",
        body="snapshot",
    )
    assert row is not None
    assert row.current_version_number == 1
    listed = await versions.list_versions(row.id, owner.id, project.id)
    assert len(listed) == 1
    assert listed[0].body == "snapshot"
