"""Phase 5.6 — orchestrator agent MVP (delegation via LangGraph handoff)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.agents.templates import DEFAULT_AGENT_TEMPLATES
from app.core.config import get_settings
from app.graphs.checkpoints import InMemoryGraphCheckpointStore
from app.graphs.handoff import (
    HANDOFF_STATUS_DELEGATED,
    build_child_run_input_payload,
    extract_handoff_controls,
)
from app.marketing.orchestration import (
    build_specialist_child_payload,
    parse_orchestration_config,
    resolve_specialist_agent_type,
)
from app.prompts.contracts import PromptBuildInput
from app.prompts.message_builder import build_llm_messages
from app.prompts.templates import DEFAULT_SYSTEM_PROMPTS
from app.schemas.contracts import AgentType
from app.tools.marketing_tools import CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME
from app.tools.registry import get_tool_registry
from app.tools.write_tool_settings import content_asset_create_draft_enabled
from fastapi.testclient import TestClient
from tests.researcher_tool_names import (
    RESEARCHER_READ_ONLY_TOOL_COUNT,
    RESEARCHER_READ_ONLY_TOOL_NAMES,
)

ORCHESTRATOR_CAPABILITY_NAMES = [
    "read_project_context",
    "read_marketing_briefs",
    "read_content_assets",
    "read_marketing_funnels",
    "analyze_funnel_gaps",
    "delegate_to_specialists",
    "coordinate_marketing_workflow",
]


@pytest.fixture
def enable_create_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_WRITE_TOOL_CONTENT_ASSET_CREATE_DRAFT_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _patch_runner_with_store(store: InMemoryGraphCheckpointStore):
    from app.graphs.runner import AgentGraphRunner as RealRunner

    class _RunnerWithStore(RealRunner):
        def __init__(self, *args, **kwargs):
            kwargs["checkpoint_store"] = store
            super().__init__(*args, **kwargs)

    return patch("app.api.routes.agent_runs.AgentGraphRunner", _RunnerWithStore)


def _project_id(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Orchestrator Project",
) -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def _agent(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_type: str,
    name: str,
    config_patch: dict | None = None,
) -> dict:
    body: dict = {"project_id": project_id, "type": agent_type, "name": name}
    response = client.post("/agents", json=body, headers=headers)
    assert response.status_code == 201
    agent = response.json()
    if config_patch:
        merged = {**agent["config"], **config_patch}
        patch_resp = client.patch(
            f"/agents/{agent['id']}",
            json={"config": merged},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        agent = patch_resp.json()
    return agent


def test_orchestrator_template_capabilities_and_config() -> None:
    template = DEFAULT_AGENT_TEMPLATES[AgentType.ORCHESTRATOR]
    names = [cap.name for cap in template["capabilities"]]
    assert names == ORCHESTRATOR_CAPABILITY_NAMES
    cfg = template["default_config"]
    assert cfg["tools"]["profile"] == "orchestrator"
    assert cfg["llm"]["temperature"] == 0.2
    assert cfg["orchestration"]["handoff_enabled"] is True
    assert cfg["orchestration"]["max_child_runs"] == 3
    assert cfg["orchestration"]["default_inline_child_execution"] is False


def test_orchestrator_prompt_forbids_approve_publish_and_direct_specialist_drafts() -> None:
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.ORCHESTRATOR].lower()
    assert "approve" in prompt
    assert "publish" in prompt
    assert "delegate" in prompt
    assert "content_asset.create_draft" in prompt
    assert "specialist" in prompt


def test_orchestrator_prompt_builder_includes_run_context() -> None:
    brief_id = str(uuid4())
    funnel_id = str(uuid4())
    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.ORCHESTRATOR,
            agent_config={},
            input_payload={
                "goal": "coordinate launch content",
                "brief_id": brief_id,
                "funnel_id": funnel_id,
                "research_topic": "competitors",
            },
        ),
    )
    user_message = next(message for message in built.messages if message.role == "user")
    assert brief_id in user_message.content
    assert funnel_id in user_message.content
    assert "coordinate launch content" in user_message.content
    assert "competitors" in user_message.content


def test_orchestrator_sees_all_read_only_tools() -> None:
    tools = get_tool_registry().list_for_agent(AgentType.ORCHESTRATOR)
    names = [tool.name for tool in tools]
    for expected in RESEARCHER_READ_ONLY_TOOL_NAMES:
        assert expected in names
    assert len([n for n in names if n in RESEARCHER_READ_ONLY_TOOL_NAMES]) == (
        RESEARCHER_READ_ONLY_TOOL_COUNT
    )


def test_orchestrator_write_tool_visible_but_prompt_discourages_specialist_misuse(
    enable_create_draft: None,
) -> None:
    tools = {tool.name for tool in get_tool_registry().list_for_agent(AgentType.ORCHESTRATOR)}
    assert content_asset_create_draft_enabled()
    assert CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME in tools
    prompt = DEFAULT_SYSTEM_PROMPTS[AgentType.ORCHESTRATOR].lower()
    assert "do not create content assets via content_asset.create_draft" in prompt


@pytest.mark.parametrize(
    ("goal", "extra", "expected"),
    [
        ("research audience unknowns", {}, AgentType.RESEARCHER),
        ("define positioning strategy", {}, AgentType.STRATEGIST),
        ("build content plan for funnel", {}, AgentType.CONTENT_PLANNER),
        ("write email copy for step", {"step_id": str(uuid4())}, AgentType.COPYWRITER),
        ("review this asset before approval", {"source_asset_id": str(uuid4())}, AgentType.CRITIC),
        ("", {"research_topic": "competitors"}, AgentType.RESEARCHER),
    ],
)
def test_resolve_specialist_agent_type_from_goal(
    goal: str,
    extra: dict,
    expected: AgentType,
) -> None:
    payload = {"goal": goal, **extra}
    assert resolve_specialist_agent_type(payload) == expected


def test_build_specialist_child_payload_conventions() -> None:
    brief_id = str(uuid4())
    funnel_id = str(uuid4())
    step_id = str(uuid4())
    source_id = str(uuid4())
    parent = {
        "brief_id": brief_id,
        "funnel_id": funnel_id,
        "step_id": step_id,
        "source_asset_id": source_id,
        "asset_type": "email",
        "research_topic": "topic",
        "goal": "launch",
    }
    researcher = build_specialist_child_payload(AgentType.RESEARCHER, parent)
    assert researcher == {
        "brief_id": brief_id,
        "funnel_id": funnel_id,
        "research_topic": "topic",
        "goal": "launch",
    }
    copywriter = build_specialist_child_payload(AgentType.COPYWRITER, parent)
    assert copywriter["brief_id"] == brief_id
    assert copywriter["step_id"] == step_id
    assert copywriter["asset_type"] == "email"


def test_extract_handoff_strips_target_agent_type() -> None:
    cleaned, request, hint = extract_handoff_controls(
        {
            "goal": "plan",
            "handoff_target_agent_type": "content_planner",
        },
    )
    assert request is None
    assert hint == AgentType.CONTENT_PLANNER
    assert "handoff_target_agent_type" not in cleaned


def test_mock_orchestrator_graph_handoff_creates_child_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    planner = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="content_planner",
        name="Planner",
    )
    orchestrator = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orch",
        config_patch={"mock_orchestrator_flow": True},
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator["id"],
            "input_payload": {
                "goal": "build content plan for launch funnel",
                "brief_id": str(uuid4()),
            },
        },
        headers=auth_headers,
    ).json()

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 200
    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    handoff = parent["output_payload"]["handoff"]
    assert handoff["status"] == HANDOFF_STATUS_DELEGATED
    assert handoff["target_agent_type"] == "content_planner"
    assert handoff["child_run_id"]
    assert handoff["child_run_enqueued"] is True
    assert handoff["child_run_pending_worker"] is True

    child = client.get(f"/agent-runs/{handoff['child_run_id']}", headers=auth_headers).json()
    assert child["agent_id"] == planner["id"]
    assert child["status"] == "queued"
    assert child["input_payload"]["goal"] == "build content plan for launch funnel"


def test_handoff_target_agent_type_routes_to_strategist(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers, "Type hint routing")
    strategist = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="strategist",
        name="Strategist",
    )
    orchestrator = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orch",
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator["id"],
            "input_payload": {
                "goal": "positioning gaps",
                "handoff_target_agent_type": "strategist",
            },
        },
        headers=auth_headers,
    ).json()

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    assert parent["output_payload"]["handoff"]["target_agent_id"] == strategist["id"]


@pytest.mark.asyncio
async def test_max_child_runs_blocks_second_handoff(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
) -> None:
    from uuid import UUID

    from app.db.models.agent_run import AgentRunTable
    from app.graphs.handoff import build_child_run_metadata
    from app.schemas.contracts import AgentRunStatus

    project_id = _project_id(client, auth_headers, "Max children")
    project_uuid = UUID(project_id)
    researcher = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher",
    )
    orchestrator = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orch",
        config_patch={
            "orchestration": {
                "handoff_enabled": True,
                "max_child_runs": 1,
                "default_inline_child_execution": False,
            },
        },
    )
    parent_run = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator["id"],
            "input_payload": {
                "prompt": "delegate",
                "handoff_to_agent_id": researcher["id"],
            },
        },
        headers=auth_headers,
    ).json()

    owner_id = UUID(parent_run["owner_id"])
    existing_child = AgentRunTable(
        owner_id=owner_id,
        project_id=project_uuid,
        agent_id=UUID(researcher["id"]),
        status=AgentRunStatus.QUEUED,
        input_payload={"goal": "seed"},
        run_metadata=build_child_run_metadata(
            parent_run_id=UUID(parent_run["id"]),
            trace_id="seed-trace",
            handoff_depth=1,
        ),
    )
    db_session.add(existing_child)
    await db_session.commit()

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        response = client.post(
            f"/agent-runs/{parent_run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    assert response.status_code == 500
    assert "handoff_max_children_exceeded" in response.json()["detail"]


def test_default_inline_child_execution_queues_child(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    researcher = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher",
    )
    orchestrator = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orch",
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator["id"],
            "input_payload": {
                "goal": "research competitors",
                "handoff_to_agent_id": researcher["id"],
            },
        },
        headers=auth_headers,
    ).json()

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    parent = client.get(f"/agent-runs/{run['id']}", headers=auth_headers).json()
    handoff = parent["output_payload"]["handoff"]
    assert handoff["child_run_executed"] is False
    assert handoff["child_run_pending_worker"] is True
    child = client.get(f"/agent-runs/{handoff['child_run_id']}", headers=auth_headers).json()
    assert child["status"] == "queued"


def test_classic_executor_does_not_handoff(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _project_id(client, auth_headers)
    researcher = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher",
    )
    orchestrator = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orch",
        config_patch={"mock_orchestrator_flow": True},
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator["id"],
            "input_payload": {
                "goal": "plan content",
                "handoff_to_agent_id": researcher["id"],
            },
        },
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/agent-runs/{run['id']}/execute-dry-run",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert "handoff" not in body.get("output_payload", {})


def test_orchestrator_handoff_checkpoints_recorded(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    from uuid import UUID

    project_id = _project_id(client, auth_headers)
    researcher = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="researcher",
        name="Researcher",
    )
    orchestrator = _agent(
        client,
        auth_headers,
        project_id,
        agent_type="orchestrator",
        name="Orch",
    )
    run = client.post(
        "/agent-runs",
        json={
            "agent_id": orchestrator["id"],
            "input_payload": {
                "goal": "research topic",
                "handoff_to_agent_id": researcher["id"],
            },
        },
        headers=auth_headers,
    ).json()

    store = InMemoryGraphCheckpointStore()
    with _patch_runner_with_store(store):
        client.post(
            f"/agent-runs/{run['id']}/execute-graph-dry-run",
            headers=auth_headers,
        )
    rows = asyncio.run(store.list_for_run(UUID(run["id"])))
    node_names = {row.node_name for row in rows}
    assert "handoff_gate" in node_names
    assert "handoff_record" in node_names


def test_child_payload_includes_specialist_fields() -> None:
    from app.graphs.handoff import GraphHandoffDecision, GraphHandoffOptions

    brief_id = str(uuid4())
    decision = GraphHandoffDecision(
        status=HANDOFF_STATUS_DELEGATED,
        target_agent_id=uuid4(),
        target_agent_type="researcher",
        target_agent_name="Researcher",
        reason="needs research",
        error=None,
        options=GraphHandoffOptions(),
    )
    child = build_child_run_input_payload(
        parent_payload={
            "brief_id": brief_id,
            "research_topic": "audience",
            "goal": "memo",
        },
        decision=decision,
        parent_run_id=uuid4(),
        source_agent_id=uuid4(),
        source_agent_type="orchestrator",
        memory_context=None,
    )
    assert child["brief_id"] == brief_id
    assert child["research_topic"] == "audience"
    assert child["goal"] == "memo"


def test_parse_orchestration_config_defaults() -> None:
    cfg = parse_orchestration_config({})
    assert cfg.handoff_enabled is True
    assert cfg.max_child_runs == 3
    assert cfg.default_inline_child_execution is False


def test_orchestrator_handoff_child_replay_after_dlq(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.test_handoff_dlq_replay import _dead_letter_child

    asyncio.run(__import__("app.core.redis", fromlist=["get_redis"]).get_redis().flushall())
    parent, child_id, _project_id = _dead_letter_child(client, auth_headers, monkeypatch)
    response = client.post(f"/agent-runs/{child_id}/handoff/replay", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["replayed"] is True
    parent_after = client.get(f"/agent-runs/{parent['id']}", headers=auth_headers).json()
    assert parent_after["output_payload"]["handoff"]["child_run_status"] == "queued"
