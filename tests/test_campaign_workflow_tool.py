"""Phase 13.1 — marketing_campaign.workflow read tool."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from app.db.models.project import ProjectTable
from app.db.repositories.tool_execution_logs import ToolExecutionLogRepository
from app.schemas.contracts import AgentType
from app.services.tool_execution_log_service import ToolExecutionLogService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME
from app.tools.permissions import ToolExecutionMode, evaluate_tool_access, get_tool_access_mode
from app.tools.registry import get_tool_registry
from app.prompts.templates import DEFAULT_SYSTEM_PROMPTS, _CAMPAIGN_WORKFLOW_GUIDANCE
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

LEAK_MARKERS = (
    "plan_payload",
    "target_audience",
    "key_message",
    "Secret notes",
    "super-secret-body",
    "campaign_metadata",
    "delivery",
    "channel_config",
    "token",
    "sk-secret",
)

_WORKFLOW_ALLOWED = (
    AgentType.STRATEGIST,
    AgentType.ORCHESTRATOR,
    AgentType.CONTENT_PLANNER,
    AgentType.ANALYST,
)

_WORKFLOW_DENIED = (
    AgentType.COPYWRITER,
    AgentType.RESEARCHER,
    AgentType.CRITIC,
)


def _project_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _campaign(client: TestClient, headers: dict[str, str], project_id: str, *, title: str) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns",
        json={
            "title": title,
            "status": "active",
            "campaign_metadata": {"secret": "nope"},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _sample_plan_payload() -> dict:
    return {
        "goal": "Launch",
        "target_audience": "SMB",
        "key_message": "Automate",
        "content_items": [
            {
                "title": "Item 0",
                "channel": "telegram",
                "format": "text",
                "scheduled_at": "2026-06-04T15:00:00Z",
                "notes": "Secret notes 0",
            },
        ],
    }


def _create_plan_draft(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
) -> str:
    resp = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts",
        json={"title": "Plan", "plan_payload": _sample_plan_payload()},
        headers=headers,
    )
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
async def test_workflow_tool_returns_compact_state(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "WF tool")
    campaign_id = _campaign(client, auth_headers, project_id, title="C tool")
    _create_plan_draft(client, auth_headers, project_id, campaign_id)

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

    result = await executor.execute(
        ToolCall(
            id="t_workflow",
            name=MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
            arguments={"campaign_id": campaign_id},
        ),
        context,
    )

    assert result.status == "succeeded"
    assert isinstance(result.output, dict)
    assert result.output.get("ok") is True
    data = result.output["data"]
    assert set(data.keys()) == {
        "campaign_id",
        "workflow_state",
        "next_recommended_action",
        "counts",
    }
    assert data["campaign_id"] == campaign_id
    assert data["workflow_state"] == "plan_ready"
    assert data["next_recommended_action"] == "generate_assets"
    assert data["counts"]["plan_drafts"] == 1
    assert data["counts"]["assets_total"] == 0


@pytest.mark.asyncio
async def test_workflow_tool_enforces_owner_scope(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "WF scope")
    other_project_id = _project_id(client, other_auth_headers, "WF other")
    other_campaign_id = _campaign(client, other_auth_headers, other_project_id, title="C other")

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
        agent_type=AgentType.ORCHESTRATOR,
    )

    denied = await executor.execute(
        ToolCall(
            id="t_denied",
            name=MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
            arguments={"campaign_id": other_campaign_id},
        ),
        context,
    )
    assert denied.status == "failed"
    assert isinstance(denied.output, dict)
    assert denied.output["ok"] is False


@pytest.mark.asyncio
async def test_workflow_tool_includes_pending_review_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "WF tool pending")
    campaign_id = _campaign(client, auth_headers, project_id, title="C pending")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)
    client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts/{draft_id}/generate-assets",
        headers=auth_headers,
    )

    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    owner_id = await _owner_id_for_project(db_session, project_id)
    result = await executor.execute(
        ToolCall(
            id="t_pending",
            name=MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
            arguments={"campaign_id": campaign_id},
        ),
        _ctx(owner_id=owner_id, project_id=project_id, agent_type=AgentType.STRATEGIST),
    )
    assert result.status == "succeeded"
    data = result.output["data"]
    assert data["workflow_state"] == "ready_for_review"
    assert data["counts"]["pending_review_assets"] == 1
    assert data["next_recommended_action"] == "human_review_required"
    assert "pending_review_assets" in data["counts"]


@pytest.mark.asyncio
async def test_workflow_tool_has_no_content_leaks(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "WF leaks")
    campaign_id = _campaign(client, auth_headers, project_id, title="C leaks")
    draft_id = _create_plan_draft(client, auth_headers, project_id, campaign_id)
    gen = client.post(
        f"/projects/{project_id}/campaigns/{campaign_id}/plan-drafts/{draft_id}/generate-assets",
        headers=auth_headers,
    )
    assert gen.status_code in {200, 201}, gen.text
    asset_id = gen.json()["asset_ids"][0]
    patch = client.patch(
        f"/projects/{project_id}/content-assets/{asset_id}",
        json={"body": "super-secret-body"},
        headers=auth_headers,
    )
    assert patch.status_code == 200, patch.text

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
    result = await executor.execute(
        ToolCall(
            id="t_leaks",
            name=MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
            arguments={"campaign_id": campaign_id},
        ),
        context,
    )
    assert result.status == "succeeded"
    blob = json.dumps(result.output).lower()
    for marker in LEAK_MARKERS:
        assert marker.lower() not in blob


@pytest.mark.asyncio
async def test_workflow_tool_writes_audit_log(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _project_id(client, auth_headers, "WF audit")
    campaign_id = _campaign(client, auth_headers, project_id, title="C audit")

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
        agent_type=AgentType.ANALYST,
    )
    result = await executor.execute(
        ToolCall(
            id="t_audit",
            name=MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
            arguments={"campaign_id": campaign_id},
        ),
        context,
    )
    assert result.status == "succeeded"

    repo = ToolExecutionLogRepository(db_session)
    logs = await repo.list_by_project(
        UUID(owner_id),
        UUID(project_id),
        limit=20,
        offset=0,
    )
    assert any(row.tool_name == MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME for row in logs)


def test_workflow_tool_allowlist_and_denylist() -> None:
    registry = get_tool_registry()
    tool = registry.get(MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME)
    assert get_tool_access_mode(tool) == ToolExecutionMode.READ_ONLY

    for agent_type in _WORKFLOW_ALLOWED:
        names = {t.name for t in registry.list_for_agent(agent_type)}
        assert MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME in names
        decision = evaluate_tool_access(
            agent_type=agent_type,
            tool_name=MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
            tool=tool,
        )
        assert decision.allowed is True
        assert decision.execution_mode == ToolExecutionMode.READ_ONLY

    for agent_type in _WORKFLOW_DENIED:
        names = {t.name for t in registry.list_for_agent(agent_type)}
        assert MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME not in names
        decision = evaluate_tool_access(
            agent_type=agent_type,
            tool_name=MARKETING_CAMPAIGN_WORKFLOW_TOOL_NAME,
            tool=tool,
        )
        assert decision.allowed is False


@pytest.mark.parametrize(
    "agent_type",
    [
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CONTENT_PLANNER,
    ],
)
def test_prompt_templates_include_workflow_guidance(agent_type: AgentType) -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[agent_type].lower()
    guidance = _CAMPAIGN_WORKFLOW_GUIDANCE.lower()
    assert "marketing_campaign.workflow" in prompt
    assert guidance.split("\n")[0] in prompt or "inspect campaign workflow" in prompt
    assert "never approve" in prompt
    assert "schedule" in prompt


def test_copywriter_prompt_lacks_workflow_tool_guidance() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.COPYWRITER].lower()
    assert "marketing_campaign.workflow" not in prompt
