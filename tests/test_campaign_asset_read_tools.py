"""Phase 12.0 — campaign/content asset read-only agent tools."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from app.db.models.project import ProjectTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.schemas.contracts import AgentType
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.asset_read_settings import CAMPAIGN_ASSET_LIST_TOOL_NAME
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import CONTENT_ASSET_GET_TOOL_NAME, CONTENT_ASSET_LIST_TOOL_NAME
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _tool_data(result) -> dict:
    assert result.output["ok"] is True
    return result.output["data"]


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign(client: TestClient, headers: dict[str, str], project_id: str, *, title: str) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": title, "status": "active"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _sample_plan_payload(*, item_count: int = 1) -> dict:
    items = [
        {
            "title": f"Item {index}",
            "channel": "telegram",
            "format": "text",
            "scheduled_at": "2026-06-04T15:00:00Z",
            "notes": f"Notes {index}",
        }
        for index in range(item_count)
    ]
    return {
        "goal": "Launch",
        "target_audience": "SMB",
        "key_message": "Automate",
        "content_items": items,
    }


def _plan_drafts_url(project_id: str, campaign_id: str) -> str:
    return f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts"


def _generate_assets_url(project_id: str, campaign_id: str, draft_id: str) -> str:
    return f"{_plan_drafts_url(project_id, campaign_id)}/{draft_id}/generate-assets"


def _create_plan_draft_and_assets(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
    *,
    item_count: int = 2,
) -> tuple[str, list[str]]:
    draft_resp = client.post(
        _plan_drafts_url(project_id, campaign_id),
        json={
            "title": "June plan",
            "plan_payload": _sample_plan_payload(item_count=item_count),
        },
        headers=headers,
    )
    assert draft_resp.status_code == 201, draft_resp.text
    draft_id = draft_resp.json()["id"]
    gen = client.post(_generate_assets_url(project_id, campaign_id, draft_id), headers=headers)
    assert gen.status_code in {200, 201}, gen.text
    asset_ids = gen.json()["asset_ids"]
    assert len(asset_ids) == item_count
    return draft_id, asset_ids


def _ctx(*, owner_id: str, project_id: str, agent_type: AgentType) -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=UUID(owner_id),
        project_id=UUID(project_id),
        agent_id=uuid4(),
        agent_type=agent_type,
        agent_run_id=uuid4(),
        request_id=str(uuid4()),
    )


async def _owner_id_for_project(db_session: AsyncSession, project_id: str) -> str:
    row = await db_session.get(ProjectTable, UUID(project_id))
    assert row is not None
    return str(row.owner_id)


@pytest.mark.asyncio
async def test_campaign_asset_list_by_campaign_id(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 list")
    campaign_id = _campaign(client, auth_headers, project_id, title="C list")
    _draft_id, asset_ids = _create_plan_draft_and_assets(
        client,
        auth_headers,
        project_id,
        campaign_id,
        item_count=2,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    context = _ctx(
        owner_id=owner_id,
        project_id=project_id,
        agent_type=AgentType.CONTENT_PLANNER,
    )
    result = await executor.execute(
        ToolCall(
            id="call_cal",
            name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
            arguments={"campaign_id": campaign_id, "limit": 10},
        ),
        context,
    )
    assert result.status == "succeeded"
    items = _tool_data(result)["items"]
    listed_ids = {item["id"] for item in items}
    assert set(asset_ids) <= listed_ids
    assert all(item["campaign_id"] == campaign_id for item in items)
    assert all(item["status"] == "draft" for item in items)


@pytest.mark.asyncio
async def test_content_asset_get_draft_with_body_for_copywriter(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 get")
    campaign_id = _campaign(client, auth_headers, project_id, title="C get")
    _draft_id, asset_ids = _create_plan_draft_and_assets(
        client,
        auth_headers,
        project_id,
        campaign_id,
        item_count=1,
    )
    asset_id = asset_ids[0]

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    context = _ctx(
        owner_id=owner_id,
        project_id=project_id,
        agent_type=AgentType.COPYWRITER,
    )
    result = await executor.execute(
        ToolCall(
            id="call_cag",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": asset_id, "include_body": True},
        ),
        context,
    )
    assert result.status == "succeeded"
    asset = _tool_data(result)["asset"]
    assert asset["status"] == "draft"
    assert asset["body"]
    assert "source_plan_draft_id" in str(asset.get("metadata", {}))


@pytest.mark.asyncio
async def test_list_does_not_expose_full_body(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 no body list")
    campaign_id = _campaign(client, auth_headers, project_id, title="C no body")
    _create_plan_draft_and_assets(client, auth_headers, project_id, campaign_id)

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    context = _ctx(
        owner_id=owner_id,
        project_id=project_id,
        agent_type=AgentType.STRATEGIST,
    )

    for tool_name, arguments in (
        (
            CAMPAIGN_ASSET_LIST_TOOL_NAME,
            {"campaign_id": campaign_id, "limit": 10},
        ),
        (
            CONTENT_ASSET_LIST_TOOL_NAME,
            {"campaign_id": campaign_id, "limit": 10},
        ),
    ):
        result = await executor.execute(
            ToolCall(id=f"call_{tool_name}", name=tool_name, arguments=arguments),
            context,
        )
        assert result.status == "succeeded"
        for item in _tool_data(result)["items"]:
            assert "body" not in item
            assert "body_preview" in item


@pytest.mark.asyncio
async def test_get_body_denied_for_analyst(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 analyst")
    campaign_id = _campaign(client, auth_headers, project_id, title="C analyst")
    _draft_id, asset_ids = _create_plan_draft_and_assets(
        client,
        auth_headers,
        project_id,
        campaign_id,
        item_count=1,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    context = _ctx(
        owner_id=owner_id,
        project_id=project_id,
        agent_type=AgentType.ANALYST,
    )

    denied_get = await executor.execute(
        ToolCall(
            id="call_analyst_get",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": asset_ids[0]},
        ),
        context,
    )
    assert denied_get.status == "failed"
    assert denied_get.output["ok"] is False

    denied_body = await executor.execute(
        ToolCall(
            id="call_analyst_body",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": asset_ids[0], "include_body": True},
        ),
        context,
    )
    assert denied_body.status == "failed"


@pytest.mark.asyncio
async def test_researcher_does_not_see_content_asset_tools() -> None:
    tools = {t.name for t in get_tool_registry().list_for_agent(AgentType.RESEARCHER)}
    assert "content_asset.get" not in tools
    assert "content_asset.list" not in tools
    assert CAMPAIGN_ASSET_LIST_TOOL_NAME not in tools


@pytest.mark.asyncio
async def test_ownership_guard_denies_foreign_project_asset(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 mine")
    other_project_id = _project_id(client, other_auth_headers, "P12 other")
    other_campaign_id = _campaign(client, other_auth_headers, other_project_id, title="C other")
    _draft_id, other_asset_ids = _create_plan_draft_and_assets(
        client,
        other_auth_headers,
        other_project_id,
        other_campaign_id,
        item_count=1,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    context = _ctx(
        owner_id=owner_id,
        project_id=project_id,
        agent_type=AgentType.COPYWRITER,
    )

    denied_get = await executor.execute(
        ToolCall(
            id="call_denied_get",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": other_asset_ids[0], "include_body": True},
        ),
        context,
    )
    assert denied_get.status == "failed"
    assert denied_get.output["error"]["code"] in {"not_found", "permission_denied"}

    denied_list = await executor.execute(
        ToolCall(
            id="call_denied_list",
            name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
            arguments={"campaign_id": other_campaign_id, "limit": 10},
        ),
        context,
    )
    assert denied_list.status == "succeeded"
    assert _tool_data(denied_list)["count"] == 0


@pytest.mark.asyncio
async def test_get_does_not_leak_version_history_bodies(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 versions")
    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Versioned", "body": "version-one-secret-body"},
        headers=auth_headers,
    ).json()
    patched = client.patch(
        f"/projects/{project_id}/content-assets/{asset['id']}",
        json={"body": "version-two-secret-body"},
        headers=auth_headers,
    )
    assert patched.status_code == 200

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    context = _ctx(
        owner_id=owner_id,
        project_id=project_id,
        agent_type=AgentType.COPYWRITER,
    )
    result = await executor.execute(
        ToolCall(
            id="call_versions",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": asset["id"], "include_body": True},
        ),
        context,
    )
    assert result.status == "succeeded"
    payload = _tool_data(result)["asset"]
    assert "versions" not in payload
    assert payload["body"] == "version-two-secret-body"
    assert "version-one-secret-body" not in str(result.output)


@pytest.mark.asyncio
async def test_metadata_secrets_redacted_in_list(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 meta")
    client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": "Secret meta",
            "body": "short",
            "metadata": {"api_key": "sk-should-not-appear", "source_plan_draft_id": "draft-1"},
        },
        headers=auth_headers,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    context = _ctx(
        owner_id=owner_id,
        project_id=project_id,
        agent_type=AgentType.CONTENT_PLANNER,
    )
    result = await executor.execute(
        ToolCall(
            id="call_meta_list",
            name=CONTENT_ASSET_LIST_TOOL_NAME,
            arguments={"limit": 5},
        ),
        context,
    )
    assert result.status == "succeeded"
    item = _tool_data(result)["items"][0]
    meta = item["metadata"]
    assert meta.get("_redacted") is True
    assert "sk-should-not-appear" not in str(result.output)


@pytest.mark.asyncio
async def test_read_tools_write_audit_log(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P12 audit")
    campaign_id = _campaign(client, auth_headers, project_id, title="C audit")
    _draft_id, asset_ids = _create_plan_draft_and_assets(
        client,
        auth_headers,
        project_id,
        campaign_id,
        item_count=1,
    )

    audit = ToolExecutionLogService(db_session)
    executor = SafeNoOpToolExecutor(
        get_tool_registry(),
        session=db_session,
        audit_service=audit,
    )
    owner_id = await _owner_id_for_project(db_session, project_id)
    context = _ctx(
        owner_id=owner_id,
        project_id=project_id,
        agent_type=AgentType.STRATEGIST,
    )

    await executor.execute(
        ToolCall(
            id="call_audit_list",
            name=CAMPAIGN_ASSET_LIST_TOOL_NAME,
            arguments={"campaign_id": campaign_id, "limit": 5},
        ),
        context,
    )
    await executor.execute(
        ToolCall(
            id="call_audit_get",
            name=CONTENT_ASSET_GET_TOOL_NAME,
            arguments={"asset_id": asset_ids[0], "include_body": True},
        ),
        context,
    )

    repo = ToolExecutionLogRepository(db_session)
    logs = await repo.list_by_project(UUID(owner_id), UUID(project_id), limit=20, offset=0)
    logged = {row.tool_name for row in logs}
    assert CAMPAIGN_ASSET_LIST_TOOL_NAME in logged
    assert CONTENT_ASSET_GET_TOOL_NAME in logged
