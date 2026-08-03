"""Phase AI.39 — Marketing pipeline production freeze invariants (AI.27–AI.38)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.llm import LLMRequestTable
from app.db.models.marketing_plan import MarketingPlanTable, MarketingPlanVersionTable
from app.db.models.marketing_specialist_output import MarketingSpecialistOutputVersionTable
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.schemas.agent_chat import AgentChatSendResponse
from app.schemas.contracts import (
    ChatBlockActionType,
    MarketingPlanExecutionStatus,
    MarketingPlanExecutionTaskSnapshot,
    MarketingPlanExecutionTaskStatus,
    MarketingPlanStatus,
    MarketingSpecialistOutputStatus,
    MarketingSpecialistType,
)
from app.services.agent_runs import AgentRunService
from app.services.marketing_pipeline_execution_service import (
    MarketingPipelineExecutionService,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"

# Frozen subset from AI.26 chat send contract — marketing pipeline must not shrink this surface.
AI_26_FROZEN_POST_CHAT_RESPONSE_KEYS = frozenset(
    {
        "session",
        "session_id",
        "user_message",
        "assistant_message",
        "assistant_message_id",
        "agent_run_id",
        "execution_metadata",
        "output",
        "blocks",
    },
)

PIPELINE_ORDER = MarketingPipelineExecutionService.pipeline_order()

SPECIALIST_OUTPUT_TYPES: dict[MarketingSpecialistType, str] = {
    MarketingSpecialistType.STRATEGIST: "strategy",
    MarketingSpecialistType.RESEARCHER: "research",
    MarketingSpecialistType.CONTENT_PLANNER: "content_plan",
    MarketingSpecialistType.COPYWRITER: "content_copy",
    MarketingSpecialistType.CRITIC: "critique",
    MarketingSpecialistType.ANALYST: "analysis",
}

DEPENDENCY_BLOCK_CASES: tuple[tuple[MarketingSpecialistType, str], ...] = (
    (MarketingSpecialistType.RESEARCHER, "Researcher requires completed Strategist output"),
    (MarketingSpecialistType.CONTENT_PLANNER, "Content Planner requires completed Researcher output"),
    (MarketingSpecialistType.COPYWRITER, "Copywriter requires completed Content Planner output"),
    (MarketingSpecialistType.CRITIC, "Critic requires completed Copywriter output"),
    (MarketingSpecialistType.ANALYST, "Analyst requires completed Critic output"),
)


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.39 Freeze"}, headers=headers)
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


def _chat(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    agent_id: str,
    content: str = STRATEGY_MESSAGE,
) -> dict:
    response = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": content, "agent_id": agent_id},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _marketing_plan_block(body: dict) -> dict:
    blocks = body.get("blocks") or []
    plan_blocks = [b for b in blocks if b.get("type") == "marketing_plan"]
    assert plan_blocks, "expected marketing_plan block"
    return plan_blocks[0]


def _save_plan_from_chat(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    chat_body: dict,
) -> str:
    saved = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat_body["session_id"],
            "assistant_message_id": chat_body["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    return saved.json()["created_resource_id"]


def _approve_plan(client: TestClient, headers: dict[str, str], project_id: str, plan_id: str) -> None:
    approved = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 200


def _approved_plan_pipeline(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
) -> tuple[str, str]:
    orchestrator_id = _create_agent(client, headers, project_id, agent_type="orchestrator")
    chat = _chat(client, headers, project_id, agent_id=orchestrator_id)
    plan_id = _save_plan_from_chat(client, headers, project_id, chat)
    _approve_plan(client, headers, project_id, plan_id)
    return plan_id, chat


def _start_run(client: TestClient, headers: dict[str, str], project_id: str, plan_id: str) -> dict:
    created = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    started = client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}/start",
        headers=headers,
    )
    assert started.status_code == 200
    return client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}",
        headers=headers,
    ).json()


def _task_index_for(run: dict, specialist: MarketingSpecialistType) -> int:
    return next(
        index
        for index, task in enumerate(run["task_snapshots"])
        if task["specialist"] == specialist.value
    )


def _execute_specialist(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    run_id: str,
    task_index: int,
):
    return client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}/tasks/{task_index}/execute-specialist",
        headers=headers,
    )


# --- AI.26 chat contract freeze ---


def test_ai_26_post_chat_response_keys_remain_available() -> None:
    current = frozenset(AgentChatSendResponse.model_fields.keys())
    missing = AI_26_FROZEN_POST_CHAT_RESPONSE_KEYS - current
    assert not missing, f"AI.26 frozen keys removed from AgentChatSendResponse: {missing}"


# --- Planning & persistence ---


def test_marketing_chat_returns_plan_block_not_specialist_outputs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    body = _chat(client, auth_headers, project_id, agent_id=orchestrator_id)
    _marketing_plan_block(body)
    outputs = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        headers=auth_headers,
    ).json()
    assert outputs == []


def test_save_marketing_plan_action_creates_draft_plan(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(client, auth_headers, project_id, agent_id=orchestrator_id)
    plan_id = _save_plan_from_chat(client, auth_headers, project_id, chat)
    plan = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}",
        headers=auth_headers,
    ).json()
    assert plan["status"] == MarketingPlanStatus.DRAFT.value


def test_draft_plan_cannot_create_execution_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")
    chat = _chat(client, auth_headers, project_id, agent_id=orchestrator_id)
    plan_id = _save_plan_from_chat(client, auth_headers, project_id, chat)
    response = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_execution_run_snapshots_approved_version_number(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id, _chat = _approved_plan_pipeline(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    plan_row = (
        await db_session.execute(
            select(MarketingPlanTable).where(MarketingPlanTable.id == UUID(plan_id)),
        )
    ).scalar_one()
    assert run["marketing_plan_version_number"] == plan_row.approved_version_number


# --- Execution guards ---


def test_specialist_execution_requires_running_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id, _ = _approved_plan_pipeline(client, auth_headers, project_id)
    created = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=auth_headers,
    ).json()
    try:
        index = _task_index_for(created, MarketingSpecialistType.STRATEGIST)
    except StopIteration:
        pytest.skip("No strategist task in plan")
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        created["id"],
        index,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_specialist_execution_uses_persisted_run_not_chat_json(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id, _ = _approved_plan_pipeline(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    version = (
        await db_session.execute(
            select(MarketingPlanVersionTable).where(
                MarketingPlanVersionTable.marketing_plan_id == UUID(plan_id),
                MarketingPlanVersionTable.version_number
                == run["marketing_plan_version_number"],
            ),
        )
    ).scalar_one()
    version_tasks = list(version.specialist_tasks or [])
    run_objectives = [t["objective"] for t in run["task_snapshots"]]
    version_objectives = [t["objective"] for t in version_tasks if isinstance(t, dict)]
    assert run_objectives
    assert run_objectives == version_objectives


# --- Pipeline matrix ---


def test_canonical_pipeline_order_matches_mvp_six() -> None:
    assert PIPELINE_ORDER == [
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.ANALYST,
    ]


@pytest.mark.parametrize(("specialist", "expected_message"), DEPENDENCY_BLOCK_CASES)
def test_dependency_matrix_blocks_missing_prior(
    client: TestClient,
    auth_headers: dict[str, str],
    specialist: MarketingSpecialistType,
    expected_message: str,
) -> None:
    """Execute all required priors except the last one in matrix order, then expect 409."""
    project_id = _create_project(client, auth_headers)
    plan_id, _ = _approved_plan_pipeline(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    required = MarketingPipelineExecutionService.required_prior_specialists(specialist)
    satisfied_early = required[:-1] if required else []
    for role in satisfied_early:
        try:
            index = _task_index_for(run, role)
        except StopIteration:
            continue
        assert (
            _execute_specialist(client, auth_headers, project_id, run["id"], index).status_code
            == 201
        )
    try:
        blocked_index = _task_index_for(run, specialist)
    except StopIteration:
        pytest.skip(f"Plan has no {specialist.value} task")
    response = _execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        blocked_index,
    )
    assert response.status_code == 409
    assert expected_message in response.json()["detail"]


def test_non_specialist_completed_snapshots_do_not_complete_run() -> None:
    base = MarketingPlanExecutionTaskSnapshot(
        specialist=MarketingSpecialistType.STRATEGIST,
        objective="o",
        expected_output="e",
        status=MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED,
    )
    for bad_status in (
        MarketingPlanExecutionTaskStatus.PLACEHOLDER_COMPLETED,
        MarketingPlanExecutionTaskStatus.SKIPPED,
        MarketingPlanExecutionTaskStatus.PENDING,
    ):
        snapshots = [
            base,
            MarketingPlanExecutionTaskSnapshot(
                specialist=MarketingSpecialistType.RESEARCHER,
                objective="o",
                expected_output="e",
                status=bad_status,
            ),
        ]
        assert not MarketingPipelineExecutionService.all_tasks_specialist_completed(snapshots)


# --- End-to-end API smoke (full conveyor) ---


@pytest.mark.asyncio
async def test_marketing_pipeline_api_smoke_full_conveyor(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    orchestrator_id = _create_agent(client, auth_headers, project_id, agent_type="orchestrator")

    chat = _chat(client, auth_headers, project_id, agent_id=orchestrator_id)
    _marketing_plan_block(chat)

    plan_id = _save_plan_from_chat(client, auth_headers, project_id, chat)
    plan = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}",
        headers=auth_headers,
    ).json()
    assert plan["status"] == MarketingPlanStatus.DRAFT.value

    _approve_plan(client, auth_headers, project_id, plan_id)
    approved = client.get(
        f"/projects/{project_id}/marketing-plans/{plan_id}",
        headers=auth_headers,
    ).json()
    assert approved["status"] == MarketingPlanStatus.APPROVED.value

    run = _start_run(client, auth_headers, project_id, plan_id)
    assert run["status"] == MarketingPlanExecutionStatus.RUNNING.value

    owner_id = UUID(run["owner_id"])
    project_uuid = UUID(project_id)
    chat_run_id = UUID(chat["agent_run_id"])
    children_before = await AgentRunService(db_session).count_children(chat_run_id, owner_id)
    assets_before = await ContentAssetRepository(db_session).list_by_project(
        owner_id,
        project_uuid,
    )

    last_response = None
    executed_specialists: list[MarketingSpecialistType] = []

    for specialist in PIPELINE_ORDER:
        try:
            task_index = _task_index_for(run, specialist)
        except StopIteration:
            continue
        last_response = _execute_specialist(
            client,
            auth_headers,
            project_id,
            run["id"],
            task_index,
        )
        assert last_response.status_code == 201, last_response.text
        executed_specialists.append(specialist)
        body = last_response.json()
        output = client.get(
            f"/projects/{project_id}/marketing-specialist-outputs/{body['specialist_output_id']}",
            headers=auth_headers,
        ).json()
        assert output["status"] == MarketingSpecialistOutputStatus.DRAFT.value
        assert output["current_version_number"] == 1
        assert output["output_type"] == SPECIALIST_OUTPUT_TYPES[specialist]
        assert "raw_response" not in (output.get("structured_data") or {})

        version_count = (
            await db_session.execute(
                select(func.count())
                .select_from(MarketingSpecialistOutputVersionTable)
                .where(
                    MarketingSpecialistOutputVersionTable.specialist_output_id
                    == UUID(body["specialist_output_id"]),
                ),
            )
        ).scalar_one()
        assert version_count == 1

        run = client.get(
            f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
            headers=auth_headers,
        ).json()
        task = run["task_snapshots"][task_index]
        assert task["status"] == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
        assert task["output_ref"] == body["specialist_output_id"]

        if specialist != PIPELINE_ORDER[-1]:
            assert run["status"] == MarketingPlanExecutionStatus.RUNNING.value

    assert last_response is not None
    final = last_response.json()
    assert final["execution_run_status"] == MarketingPlanExecutionStatus.SUCCEEDED.value
    assert final["run_completed"] is True

    run_final = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    assert run_final["status"] == MarketingPlanExecutionStatus.SUCCEEDED.value
    summary = run_final["result_summary"]
    assert summary["mode"] == "specialist_pipeline"
    assert summary["task_count"] == len(run_final["task_snapshots"])
    for specialist in executed_specialists:
        assert specialist.value in summary["completed_specialists"]
        assert specialist.value in summary["output_ids_by_specialist"]

    children_after = await AgentRunService(db_session).count_children(chat_run_id, owner_id)
    assert children_after == children_before == 0

    assets_after = await ContentAssetRepository(db_session).list_by_project(
        owner_id,
        project_uuid,
    )
    assert len(assets_after) == len(assets_before)

    tool_count = (
        await db_session.execute(
            select(func.count())
            .select_from(ToolExecutionLogTable)
            .where(ToolExecutionLogTable.project_id == project_uuid),
        )
    ).scalar_one()
    assert tool_count == 0

    llm_rows = (
        await db_session.execute(
            select(LLMRequestTable).where(LLMRequestTable.project_id == project_uuid),
        )
    ).scalars().all()
    for row in llm_rows:
        meta = row.request_metadata or {}
        tools_meta = meta.get("tools_metadata") or {}
        available = tools_meta.get("available_tool_names")
        assert available is None or available == []
