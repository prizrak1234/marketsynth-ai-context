"""Phase 5.7 — end-to-end marketing agency workflow regression."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from app.core.config import get_settings
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.marketing.content_plan_quality import CONTENT_PLAN_PURPOSE
from app.marketing.review_quality import CONTENT_REVIEW_PURPOSE
from app.marketing.workflow_smoke import (
    agent_config_with_mock_flow,
    create_critic_run_payload,
    create_orchestrator_run_payload,
    seed_demo_marketing_workspace,
)
from app.schemas.contracts import AgentRunStatus, AgentType, EventType
from app.tools.registry import get_tool_registry
from fastapi.testclient import TestClient

_PROCESS_HANDOFF = "/agent-runs/process-handoff-children"


@pytest.fixture
def enable_create_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def workflow_client(client: TestClient, enable_create_draft: None) -> TestClient:
    get_settings.cache_clear()
    return client


def _patch_runner_with_store(store: InMemoryGraphCheckpointStore):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def _patch_agent(client: TestClient, headers: dict[str, str], agent: dict, flow_key: str) -> dict:
    config = agent_config_with_mock_flow(agent.get("config"), flow_key)
    response = client.patch(
        f"/agents/{agent['id']}",
        json={"config": config},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def _find_asset_for_run(assets: list[dict], run_id: str) -> dict | None:
    for asset in assets:
        if asset.get("agent_run_id") == run_id:
            return asset
    return None


def _find_review_for_source(assets: list[dict], source_id: str) -> dict | None:
    for asset in assets:
        meta = asset.get("metadata") or {}
        if meta.get("source_asset_id") == source_id:
            return asset
        if (
            meta.get("purpose") == CONTENT_REVIEW_PURPOSE
            and meta.get("source_asset_id") == source_id
        ):
            return asset
    return None


def test_full_marketing_workflow_e2e(
    workflow_client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    """Orchestrator → planner child → critic review → human approve."""
    client = workflow_client
    store = InMemoryGraphCheckpointStore()

    project_id = client.post(
        "/projects",
        json={"name": "E2E Marketing Workflow"},
        headers=auth_headers,
    ).json()["id"]

    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "E2E brief", "offer": "Launch offer"},
        headers=auth_headers,
    ).json()["id"]

    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "E2E funnel", "brief_id": brief_id},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "Awareness"},
        headers=auth_headers,
    )

    orchestrator = _patch_agent(
        client,
        auth_headers,
        client.post(
            "/agents",
            json={"project_id": project_id, "type": "orchestrator"},
            headers=auth_headers,
        ).json(),
        "mock_orchestrator_flow",
    )
    planner = _patch_agent(
        client,
        auth_headers,
        client.post(
            "/agents",
            json={"project_id": project_id, "type": "content_planner"},
            headers=auth_headers,
        ).json(),
        "mock_content_planner_flow",
    )
    critic = _patch_agent(
        client,
        auth_headers,
        client.post(
            "/agents",
            json={"project_id": project_id, "type": "critic"},
            headers=auth_headers,
        ).json(),
        "mock_critic_flow",
    )

    parent_run = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator["id"],
            "input_payload": create_orchestrator_run_payload(
                brief_id=brief_id,
                funnel_id=funnel_id,
            ),
        },
        headers=auth_headers,
    ).json()

    with _patch_runner_with_store(store):
        assert (
            client.post(
                f"/agent-runs/{parent_run['id']}/execute-graph-dry-run",
                headers=auth_headers,
            ).status_code
            == 200
        )
        worker = client.post(
            _PROCESS_HANDOFF,
            headers=auth_headers,
            params={"limit": 5},
        )
    assert worker.status_code == 200
    assert worker.json()["processed_count"] >= 1

    parent = client.get(f"/agent-runs/{parent_run['id']}", headers=auth_headers).json()
    handoff = parent["output_payload"]["handoff"]
    assert handoff["status"] == "delegated"
    assert handoff["target_agent_type"] == "content_planner"
    assert handoff.get("parent_handoff_synced_at")

    child_id = handoff["child_run_id"]
    child = client.get(f"/agent-runs/{child_id}", headers=auth_headers).json()
    assert child["status"] == "succeeded"
    assert child["agent_id"] == planner["id"]

    assets = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    plan_before = _find_asset_for_run(assets, child_id)
    assert plan_before is not None
    assert plan_before["status"] == "draft"
    assert (plan_before.get("metadata") or {}).get("purpose") == CONTENT_PLAN_PURPOSE

    critic_run = client.post(
        "/agent-runs",
        json={
            "agent_id": critic["id"],
            "input_payload": create_critic_run_payload(
                source_asset_id=plan_before["id"],
                brief_id=brief_id,
                funnel_id=funnel_id,
            ),
        },
        headers=auth_headers,
    ).json()

    with _patch_runner_with_store(store):
        assert (
            client.post(
                f"/agent-runs/{critic_run['id']}/execute-graph-dry-run",
                headers=auth_headers,
            ).status_code
            == 200
        )

    plan_after = client.get(
        f"/projects/{project_id}/content-assets/{plan_before['id']}",
        headers=auth_headers,
    ).json()
    assert plan_after["status"] == "draft"
    assert plan_after["title"] == plan_before["title"]

    assets_after = client.get(
        f"/projects/{project_id}/content-assets",
        headers=auth_headers,
    ).json()
    review = _find_review_for_source(assets_after, plan_before["id"])
    assert review is not None
    assert review["id"] != plan_before["id"]
    assert (review.get("metadata") or {}).get("purpose") == CONTENT_REVIEW_PURPOSE

    approved = client.post(
        f"/projects/{project_id}/content-assets/{plan_before['id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["status"] == "approved"
    assert approved_body["approved_version_number"] == 1

    events = client.get(f"/projects/{project_id}/events", headers=auth_headers).json()
    event_types = {row["event_type"] for row in events}
    assert EventType.GRAPH_HANDOFF_PARENT_SYNCED.value in event_types
    assert EventType.CONTENT_ASSET_APPROVED.value in event_types

    metrics = client.get(
        f"/projects/{project_id}/operational-metrics",
        headers=auth_headers,
    ).json()
    assert sum(metrics["agent_runs"].values()) >= 2
    assert metrics["graph_runs"].get("succeeded", 0) >= 1
    assert sum(metrics["outbox"].values()) >= 1


def test_agents_cannot_approve_or_publish_via_tools() -> None:
    forbidden = {"approve", "publish", "archive"}
    for agent_type in AgentType:
        tools = {tool.name for tool in get_tool_registry().list_for_agent(agent_type)}
        assert not forbidden.intersection(tools)
        assert "content_asset.approve" not in tools


def test_specialist_run_replay_clone_after_failure(
    workflow_client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client = workflow_client
    project_id = client.post(
        "/projects",
        json={"name": "Replay workflow"},
        headers=auth_headers,
    ).json()["id"]
    planner_id = client.post(
        "/agents",
        json={"project_id": project_id, "type": "content_planner"},
        headers=auth_headers,
    ).json()["id"]
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": planner_id,
            "input_payload": {"goal": "plan content", "prompt": "plan"},
        },
        headers=auth_headers,
    ).json()
    client.post(
        f"/agent-runs/{run['id']}/failed",
        json={"error": "simulated"},
        headers=auth_headers,
    )
    replay = client.post(
        f"/agent-runs/{run['id']}/replay",
        json={"reason": "workflow_regression"},
        headers=auth_headers,
    )
    assert replay.status_code == 201
    clone = replay.json()
    assert clone["id"] != run["id"]
    assert clone["status"] == AgentRunStatus.QUEUED.value
    assert clone["metadata"]["replay"]["source_run_id"] == run["id"]


def test_workflow_summary_requires_auth(
    workflow_client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = workflow_client.post(
        "/projects",
        json={"name": "Summary auth"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = workflow_client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    run = workflow_client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "solo"}},
        headers=auth_headers,
    ).json()
    assert workflow_client.get(f"/agent-runs/{run['id']}/workflow-summary").status_code in (
        401,
        403,
    )


def test_workflow_summary_enforces_ownership(
    workflow_client: TestClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    project_id = workflow_client.post(
        "/projects",
        json={"name": "Summary own"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = workflow_client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    run = workflow_client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "solo"}},
        headers=auth_headers,
    ).json()
    response = workflow_client.get(
        f"/agent-runs/{run['id']}/workflow-summary",
        headers=other_auth_headers,
    )
    assert response.status_code == 404


def test_workflow_summary_without_handoff_is_empty(
    workflow_client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = workflow_client.post(
        "/projects",
        json={"name": "Summary empty"},
        headers=auth_headers,
    ).json()["id"]
    agent_id = workflow_client.post(
        "/agents",
        json={"project_id": project_id, "type": "researcher"},
        headers=auth_headers,
    ).json()["id"]
    run = workflow_client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "no handoff"}},
        headers=auth_headers,
    ).json()
    summary = workflow_client.get(
        f"/agent-runs/{run['id']}/workflow-summary",
        headers=auth_headers,
    ).json()
    assert summary["parent_run_id"] == run["id"]
    assert summary["child_runs"] == []
    assert summary["handoff"] == {}


def test_workflow_summary_shows_child_and_assets(
    workflow_client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client = workflow_client
    store = InMemoryGraphCheckpointStore()
    project_id = client.post(
        "/projects",
        json={"name": "Summary handoff"},
        headers=auth_headers,
    ).json()["id"]
    brief_id = client.post(
        f"/projects/{project_id}/marketing-briefs",
        json={"title": "Brief", "offer": "Offer"},
        headers=auth_headers,
    ).json()["id"]
    funnel_id = client.post(
        f"/projects/{project_id}/funnels",
        json={"title": "Funnel", "brief_id": brief_id},
        headers=auth_headers,
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/funnels/{funnel_id}/steps",
        json={"step_type": "awareness", "title": "Step"},
        headers=auth_headers,
    )
    orchestrator = _patch_agent(
        client,
        auth_headers,
        client.post(
            "/agents",
            json={"project_id": project_id, "type": "orchestrator"},
            headers=auth_headers,
        ).json(),
        "mock_orchestrator_flow",
    )
    _patch_agent(
        client,
        auth_headers,
        client.post(
            "/agents",
            json={"project_id": project_id, "type": "content_planner"},
            headers=auth_headers,
        ).json(),
        "mock_content_planner_flow",
    )
    parent_run = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator["id"],
            "input_payload": create_orchestrator_run_payload(
                brief_id=brief_id,
                funnel_id=funnel_id,
            ),
        },
        headers=auth_headers,
    ).json()
    with _patch_runner_with_store(store):
        client.post(
            f"/agent-runs/{parent_run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
        client.post(_PROCESS_HANDOFF, headers=auth_headers, params={"limit": 5})

    summary = client.get(
        f"/agent-runs/{parent_run['id']}/workflow-summary",
        headers=auth_headers,
    ).json()
    assert summary["handoff"].get("child_run_id")
    assert len(summary["child_runs"]) == 1
    assert summary["child_runs"][0]["agent_type"] == "content_planner"
    assert summary["child_runs"][0]["created_assets"]
    assert summary["related_assets"]
    purposes = {asset["metadata_purpose"] for asset in summary["related_assets"]}
    assert CONTENT_PLAN_PURPOSE in purposes


@pytest.mark.asyncio
async def test_seed_demo_workspace_helper(
    db_session,
    database_url: str,
    fake_redis: object,
) -> None:
    from app.db.models.user import UserTable
    from app.db.repositories.user_repo import UserRepository

    owner = await UserRepository(db_session).create(UserTable(telegram_id=88077))
    workspace = await seed_demo_marketing_workspace(db_session, owner.id)
    assert workspace.project_id
    assert workspace.brief_id
    assert workspace.funnel_id
    assert workspace.orchestrator_agent_id
    assert workspace.content_planner_agent_id
    assert workspace.critic_agent_id
