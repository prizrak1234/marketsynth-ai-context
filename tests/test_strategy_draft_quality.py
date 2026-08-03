"""Phase 5.1 — strategy draft quality contract and quality endpoint."""

from __future__ import annotations

import pytest
from app.core.config import get_settings
from app.db.models.user import UserTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.user_repo import UserRepository
from app.marketing.funnel_contracts import FunnelStepType
from app.marketing.strategy_contracts import (
    DEFAULT_STRATEGY_MIN_BODY_LENGTH,
    build_mock_strategy_draft_body,
    default_strategist_draft_metadata,
    enrich_strategy_draft_metadata,
    evaluate_strategy_draft_body,
)
from app.schemas.contracts import AgentType
from app.schemas.crud import AgentCreateRequest, ProjectCreate
from app.services.agents import AgentService
from app.services.marketing_brief_service import MarketingBriefService
from app.services.marketing_funnel_service import MarketingFunnelService
from app.services.projects_service import ProjectService
from app.tools.contracts import ToolCall, ToolExecutionContext
from app.tools.executor import SafeNoOpToolExecutor
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

FULL_STRATEGY_BODY = build_mock_strategy_draft_body()


@pytest.fixture
def enable_create_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(client: TestClient, enable_create_draft: None) -> TestClient:
    get_settings.cache_clear()
    return client


def _context(owner_id, project_id, agent_id, *, agent_run_id):
    return ToolExecutionContext(
        owner_id=owner_id,
        project_id=project_id,
        agent_id=agent_id,
        agent_type=AgentType.STRATEGIST,
        agent_run_id=agent_run_id,
    )


async def _seed_stack(db_session: AsyncSession, *, telegram_id: int):
    owner = await UserRepository(db_session).create(UserTable(telegram_id=telegram_id))
    project = await ProjectService(db_session).create(
        ProjectCreate(owner_id=owner.id, name=f"Quality project {telegram_id}"),
    )
    agent = await AgentService(db_session).create_agent(
        owner.id,
        AgentCreateRequest(project_id=project.id, type=AgentType.STRATEGIST),
    )
    assert agent is not None
    brief = await MarketingBriefService(db_session).create(
        owner.id,
        project.id,
        title="Brief",
        offer="Offer",
    )
    assert brief is not None
    funnel = await MarketingFunnelService(db_session).create_funnel(
        owner.id,
        project.id,
        title="Funnel",
        brief_id=brief.id,
    )
    assert funnel is not None
    await MarketingFunnelService(db_session).create_step(
        owner.id,
        project.id,
        funnel.id,
        step_type=FunnelStepType.AWARENESS,
        title="Awareness",
    )
    return owner, project, agent, brief, funnel


def test_evaluator_detects_all_required_sections() -> None:
    quality = evaluate_strategy_draft_body(FULL_STRATEGY_BODY)
    assert quality.has_summary is True
    assert quality.has_funnel_gaps is True
    assert quality.has_recommended_assets is True
    assert quality.has_next_actions is True
    assert quality.has_risks is True
    assert quality.min_body_length_met is True
    assert quality.missing_sections == []
    assert quality.score == 1.0


def test_evaluator_detects_missing_sections() -> None:
    quality = evaluate_strategy_draft_body("## Summary\nOnly summary here.\n")
    assert quality.has_summary is True
    assert quality.has_funnel_gaps is False
    assert "Funnel gaps" in quality.missing_sections
    assert quality.score < 1.0


def test_evaluator_enforces_min_length() -> None:
    short_body = (
        "## Summary\nx\n\n## Funnel gaps\nx\n\n"
        "## Recommended assets\nx\n\n## Next actions\nx\n\n## Risks\nx"
    )
    quality = evaluate_strategy_draft_body(short_body, min_length=DEFAULT_STRATEGY_MIN_BODY_LENGTH)
    assert quality.min_body_length_met is False
    assert quality.score < 1.0


@pytest.mark.asyncio
async def test_mock_strategist_draft_gets_quality_metadata(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    from app.services.agent_runs import AgentRunService

    owner, project, agent, brief, _funnel = await _seed_stack(db_session, telegram_id=9901)
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={"goal": "quality metadata"},
        metadata={},
    )
    assert run is not None
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_quality_meta",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "brief_id": str(brief.id),
                "type": "article",
                "title": "Marketing Strategy Draft",
                "body": FULL_STRATEGY_BODY,
                "metadata": default_strategist_draft_metadata(),
            },
        ),
        _context(owner.id, project.id, agent.id, agent_run_id=run.id),
    )
    assert result.status == "succeeded"
    assets = await ContentAssetRepository(db_session).list_by_project(owner.id, project.id)
    assert len(assets) == 1
    quality = assets[0].asset_metadata.get("quality")
    assert quality is not None
    assert quality["score"] >= 0.8
    assert quality["has_summary"] is True


@pytest.mark.asyncio
async def test_low_quality_draft_still_created(
    db_session: AsyncSession,
    enable_create_draft: None,
) -> None:
    from app.services.agent_runs import AgentRunService

    owner, project, agent, _brief, _funnel = await _seed_stack(db_session, telegram_id=9902)
    run = await AgentRunService(db_session).create_run(
        owner.id,
        agent_id=agent.id,
        task_id=None,
        input_payload={},
        metadata={},
    )
    assert run is not None
    executor = SafeNoOpToolExecutor(get_tool_registry(), session=db_session)
    result = await executor.execute(
        ToolCall(
            id="call_low_quality",
            name=CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
            arguments={
                "type": "article",
                "title": "Marketing Strategy Draft",
                "body": "too short",
                "metadata": {"purpose": "marketing_strategy"},
            },
        ),
        _context(owner.id, project.id, agent.id, agent_run_id=run.id),
    )
    assert result.status == "succeeded"
    assets = await ContentAssetRepository(db_session).list_by_project(owner.id, project.id)
    assert len(assets) == 1
    assert assets[0].asset_metadata["quality"]["score"] < 0.5


def test_quality_endpoint_returns_stored_quality(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Stored quality"},
        headers=auth_headers,
    ).json()["id"]
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "article",
            "title": "Marketing Strategy Draft",
            "body": FULL_STRATEGY_BODY,
            "metadata": enrich_strategy_draft_metadata(
                default_strategist_draft_metadata(),
                FULL_STRATEGY_BODY,
            ),
        },
        headers=auth_headers,
    ).json()["id"]

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/quality",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["score"] >= 0.8
    assert body["has_summary"] is True


def test_quality_endpoint_computes_if_missing(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Computed quality"},
        headers=auth_headers,
    ).json()["id"]
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={
            "type": "article",
            "title": "Plain article",
            "body": FULL_STRATEGY_BODY,
            "metadata": {},
        },
        headers=auth_headers,
    ).json()["id"]

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/quality",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["score"] == 1.0


def test_quality_endpoint_ownership_enforced(
    client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Owned quality"},
        headers=auth_headers,
    ).json()["id"]
    asset_id = client.post(
        f"/projects/{project_id}/content-assets",
        json={"type": "email", "title": "Email", "body": "x"},
        headers=auth_headers,
    ).json()["id"]

    response = client.get(
        f"/projects/{project_id}/content-assets/{asset_id}/quality",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_strategist_end_to_end_creates_draft_with_high_score(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "E2E strategist quality"},
        headers=auth_headers,
    ).json()["id"]
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief", "offer": "Offer"},
        headers=auth_headers,
    ).json()["id"]
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Funnel"},
        headers=auth_headers,
    ).json()["id"]
    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_strategy_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {
                "brief_id": brief_id,
                "funnel_id": funnel_id,
                "goal": "create strategy draft",
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(f"/agent-runs/{run['id']}/execute-dry-run", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"

    assets = client.get(f"/projects/{project_id}/content-assets", headers=auth_headers).json()
    strategy_assets = [
        item for item in assets if item["title"] == "Marketing Strategy Draft"
    ]
    assert len(strategy_assets) == 1
    quality = client.get(
        f"/projects/{project_id}/content-assets/{strategy_assets[0]['id']}/quality",
        headers=auth_headers,
    ).json()
    assert quality["score"] > 0.8
    assert strategy_assets[0]["metadata"]["purpose"] == "marketing_strategy"


def test_classic_execute_path_quality_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Classic quality"},
        headers=auth_headers,
    ).json()["id"]
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Funnel"},
        headers=auth_headers,
    ).json()["id"]
    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_strategy_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {"funnel_id": funnel_id},
        },
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/agent-runs/{run['id']}/execute?engine=classic",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_langgraph_path_quality_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    enable_create_draft: None,
) -> None:
    project_id = client.post(
        "/projects",
        json={"name": "Graph quality"},
        headers=auth_headers,
    ).json()["id"]
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Funnel"},
        headers=auth_headers,
    ).json()["id"]
    agent = client.post(
        "/agents",
        json={"project_id": project_id, "type": "strategist"},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/agents/{agent['id']}",
        json={"config": {**agent["config"], "mock_strategy_flow": True}},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": agent["id"],
            "input_payload": {"funnel_id": funnel_id},
        },
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/agent-runs/{run['id']}/execute-graph-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert body["status"] == "succeeded"
    assert "marketing_funnel.gap_analysis" in body["output_payload"]["tools"]["tool_names"]
