"""Phase 10.0 — campaign read-only agent tools."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.db.models.project import ProjectTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.schemas.contracts import AgentType
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    title: str,
    status: str,
) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json={"title": title, "status": status, "campaign_metadata": {"secret": "nope"}},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _custom_channel(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    return client.post(
        f"/projects/{project_id}/publishing-channels",
        json={"name": "Custom", "type": "custom", "config": {"token": "super-secret"}},
        headers=headers,
    ).json()["id"]


def _approve_asset(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    title: str,
    *,
    campaign_id: str,
) -> str:
    asset = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "email",
            "title": title,
            "body": "Body with token=sk-secret",
            "campaign_id": campaign_id,
        },
        headers=headers,
    ).json()
    resp = client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/submit-review",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset['id']}/approve",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return asset["id"]


def _schedule_job(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    asset_id: str,
    channel_id: str,
    scheduled_at: datetime,
) -> str:
    payload = {
        "asset_id": asset_id,
        "channel_id": channel_id,
        "scheduled_at": scheduled_at.isoformat().replace("+00:00", "Z"),
    }
    resp = client.post(f"/projects/{project_id}/publication-jobs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


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
async def test_campaign_tools_list_get_overview_and_calendar_are_read_only_and_audited(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P tools")
    campaign_id = _campaign(client, auth_headers, project_id, title="C tools", status="active")
    channel_id = _custom_channel(client, auth_headers, project_id)
    asset_id = _approve_asset(client, auth_headers, project_id, "A1", campaign_id=campaign_id)
    _schedule_job(
        client,
        auth_headers,
        project_id,
        asset_id=asset_id,
        channel_id=channel_id,
        scheduled_at=datetime.now(tz=UTC) + timedelta(hours=2),
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

    results = []
    results.append(
        await executor.execute(
            ToolCall(id="t_list", name="marketing_campaign.list", arguments={"limit": 10}),
            context,
        ),
    )
    results.append(
        await executor.execute(
            ToolCall(
                id="t_get",
                name="marketing_campaign.get",
                arguments={"campaign_id": campaign_id},
            ),
            context,
        ),
    )
    results.append(
        await executor.execute(
            ToolCall(
                id="t_overview",
                name="marketing_campaign.overview",
                arguments={"campaign_id": campaign_id},
            ),
            context,
        ),
    )
    results.append(
        await executor.execute(
            ToolCall(
                id="t_cal",
                name="publication_calendar.list",
                arguments={"campaign_id": campaign_id, "limit": 10},
            ),
            context,
        ),
    )

    for result in results:
        assert result.status == "succeeded"
        assert isinstance(result.output, dict)
        assert result.output.get("ok") is True
        blob = str(result.output).lower()
        # No asset body/version body, no channel config, no delivery logs.
        for forbidden in ("delivery", "channel_config", "token", "sk-secret"):
            assert forbidden not in blob
        # No campaign_metadata in tools (avoid inflating context).
        assert "campaign_metadata" not in blob

    repo = ToolExecutionLogRepository(db_session)
    logs = await repo.list_by_project(
        UUID(owner_id),
        UUID(project_id),
        limit=50,
        offset=0,
    )
    logged_names = {row.tool_name for row in logs}
    assert {
        "marketing_campaign.list",
        "marketing_campaign.get",
        "marketing_campaign.overview",
        "publication_calendar.list",
    } <= logged_names


@pytest.mark.asyncio
async def test_campaign_tools_enforce_owner_project_scope(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "P mine")
    other_project_id = _project_id(client, other_auth_headers, "P other")
    other_campaign_id = _campaign(
        client,
        other_auth_headers,
        other_project_id,
        title="C other",
        status="active",
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
        agent_type=AgentType.CONTENT_PLANNER,
    )

    denied = await executor.execute(
        ToolCall(
            id="t_denied",
            name="marketing_campaign.get",
            arguments={"campaign_id": other_campaign_id},
        ),
        context,
    )
    assert denied.status == "failed"
    assert isinstance(denied.output, dict)
    assert denied.output["ok"] is False
    assert denied.output["error"]["code"] in {"not_found", "permission_denied"}


def test_tool_allowlist_campaign_tools_visibility_matrix() -> None:
    registry = get_tool_registry()
    strategist = {t.name for t in registry.list_for_agent(AgentType.STRATEGIST)}
    orchestrator = {t.name for t in registry.list_for_agent(AgentType.ORCHESTRATOR)}
    planner = {t.name for t in registry.list_for_agent(AgentType.CONTENT_PLANNER)}
    analyst = {t.name for t in registry.list_for_agent(AgentType.ANALYST)}
    copywriter = {t.name for t in registry.list_for_agent(AgentType.COPYWRITER)}
    critic = {t.name for t in registry.list_for_agent(AgentType.CRITIC)}
    researcher = {t.name for t in registry.list_for_agent(AgentType.RESEARCHER)}

    required = {
        "marketing_campaign.get",
        "marketing_campaign.list",
        "marketing_campaign.overview",
        "marketing_campaign.workflow",
        "review_queue.list",
        "publication_calendar.list",
    }
    assert required.issubset(strategist)
    assert required.issubset(orchestrator)
    assert required.issubset(planner)
    assert required.issubset(analyst)

    # copywriter: no overview (avoid inflating context), still can read list/get/calendar.
    assert {
        "marketing_campaign.get",
        "marketing_campaign.list",
        "publication_calendar.list",
    } <= copywriter
    assert "marketing_campaign.overview" not in copywriter
    assert "marketing_campaign.workflow" not in copywriter
    assert "review_queue.list" not in copywriter

    # disabled/unsupported agent types: do not expose campaign tools.
    assert required.isdisjoint(critic)
    assert required.isdisjoint(researcher)

