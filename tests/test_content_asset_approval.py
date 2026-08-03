"""Phase 4.3 — human approval workflow for content assets."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.db.models.user import UserTable
from app.db.repositories.user_repo import UserRepository
from app.marketing.asset_policy import validate_content_asset_transition
from app.marketing.contracts import ContentAssetStatus
from app.schemas.contracts import AgentType, EventType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agent_runs import AgentRunService
from app.services.agents import AgentService
from app.services.projects_service import ProjectService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/projects",
        json={"name": "Approval workflow"},
        headers=headers,
    ).json()["id"]


def _create_draft_asset(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Draft asset", "body": "copy"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    return response.json()["id"]


def _submit_and_approve(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    asset_id: str,
) -> None:
    submitted = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=headers,
    )
    assert submitted.status_code == 200
    approved = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200


def test_draft_asset_can_be_approved(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)

    _submit_and_approve(client, auth_headers, project_id, asset_id)
    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    )
    body = response.json()
    assert body["status"] == "approved"
    assert body["metadata"]["approval"]["source"] == "http_api"
    assert "approved_at" in body["metadata"]["approval"]
    assert body["metadata"]["approval"]["approved_by_owner_id"]


def test_approved_asset_cannot_be_approved_again(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_and_approve(client, auth_headers, project_id, asset_id)

    again = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )
    assert again.status_code == 409


def test_archived_asset_cannot_be_approved(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_and_approve(client, auth_headers, project_id, asset_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_approved_asset_can_be_archived(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_and_approve(client, auth_headers, project_id, asset_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_draft_can_be_archived(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_archived_asset_cannot_be_archived_again(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_and_approve(client, auth_headers, project_id, asset_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )

    again = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )
    assert again.status_code == 409


def test_ownership_enforced_on_approve_and_archive(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)

    assert (
        client.post(
            f"/projects/{project_id}/content-assets/{asset_id}/approve",
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/projects/{project_id}/content-assets/{asset_id}/archive",
            headers=other_auth_headers,
        ).status_code
        == 404
    )


def test_patch_cannot_bypass_invalid_status_transition(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_and_approve(client, auth_headers, project_id, asset_id)

    response = client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"status": "draft"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_outbox_event_created_on_approve(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_and_approve(client, auth_headers, project_id, asset_id)

    events = client.get(
        f"/projects/{project_id}/events",
        params={"event_type": EventType.CONTENT_ASSET_APPROVED.value},
        headers=auth_headers,
    ).json()
    assert len(events) >= 1
    match = next(row for row in events if row["aggregate_id"] == asset_id)
    assert match["payload"]["asset_id"] == asset_id
    assert match["payload"]["title"] == "Draft asset"
    assert "approved_at" in match["payload"]


def test_outbox_event_created_on_archive(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)
    _submit_and_approve(client, auth_headers, project_id, asset_id)
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/archive",
        headers=auth_headers,
    )

    events = client.get(
        f"/projects/{project_id}/events",
        params={"event_type": EventType.CONTENT_ASSET_ARCHIVED.value},
        headers=auth_headers,
    ).json()
    assert len(events) >= 1
    match = next(row for row in events if row["aggregate_id"] == asset_id)
    assert match["payload"]["asset_id"] == asset_id
    assert "archived_at" in match["payload"]


def test_outbox_failure_does_not_rollback_approval(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    asset_id = _create_draft_asset(client, auth_headers, project_id)

    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )
    with patch(
        "app.services.content_asset_service.EventOutboxService.append_content_asset_approved",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.post(
            f"/projects/{project_id}/content-assets/{asset_id}/approve",
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    detail = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}",
        headers=auth_headers,
    ).json()
    assert detail["status"] == "approved"


@pytest.mark.asyncio
async def test_agent_create_draft_still_creates_draft_only(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()

    owner = await UserRepository(db_session).create(UserTable(telegram_id=9801))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name="Agent draft only"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.COPYWRITER),
    )
    assert agent is not None
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"prompt": "draft"},
        metadata={},
    )
    assert run is not None

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_cd_only_draft",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={"type": "email", "title": "Agent draft", "body": "text"},
        ),
        ToolExecutionContext(
            owner_id=owner.id,
            project_id=project.id,
            agent_id=agent.id,
            agent_type=AgentType.COPYWRITER,
            agent_run_id=run.id,
        ),
    )
    assert result.status == "succeeded"
    assert result.output["ok"] is True
    assert result.output["data"]["asset"]["status"] == "draft"


def test_http_create_rejects_approved_status(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    response = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Bad", "body": "x", "status": "approved"},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_asset_policy_rejects_archived_to_draft() -> None:
    with pytest.raises(InvalidStateError):
        validate_content_asset_transition(
            ContentAssetStatus.ARCHIVED,
            ContentAssetStatus.DRAFT,
        )
