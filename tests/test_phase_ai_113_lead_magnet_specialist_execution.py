"""Phase AI.113 — Lead Magnet Specialist execution."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.schemas.contracts import (
    MarketingPlanExecutionTaskStatus,
    MarketingSpecialistType,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.v2_specialist_execution_helpers import (
    conflict_message,
    create_approved_plan_with_specialists,
    create_project,
    execute_specialist,
    execute_through,
    owner_id_for_project,
    start_run,
    task_index_for,
)

_PLAN_SPECIALISTS = [
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.FUNNEL_ARCHITECT,
    MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
]

_STRUCTURED_KEYS = (
    "lead_magnet_type",
    "title_variants",
    "promise",
    "delivery_format",
    "qualification_goal",
    "followup_recommendation",
)


@pytest.mark.asyncio
async def test_cannot_execute_lead_magnet_before_funnel_architect(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.113 Lead magnet guard")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(
        db_session,
        owner_id,
        UUID(project_id),
        _PLAN_SPECIALISTS,
    )
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(
        client,
        auth_headers,
        project_id,
        run,
        _PLAN_SPECIALISTS[:-2],
    )
    lead_index = task_index_for(run, MarketingSpecialistType.LEAD_MAGNET_SPECIALIST)
    response = execute_specialist(client, auth_headers, project_id, run["id"], lead_index)
    assert response.status_code == 409
    assert "Funnel Architect" in conflict_message(response)


@pytest.mark.asyncio
async def test_lead_magnet_executes_with_structured_output(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.113 Lead magnet happy")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(
        db_session,
        owner_id,
        UUID(project_id),
        _PLAN_SPECIALISTS,
    )
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(
        client,
        auth_headers,
        project_id,
        run,
        _PLAN_SPECIALISTS[:-1],
    )
    lead_index = task_index_for(run, MarketingSpecialistType.LEAD_MAGNET_SPECIALIST)
    response = execute_specialist(client, auth_headers, project_id, run["id"], lead_index)
    assert response.status_code == 201, response.text
    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{response.json()['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "lead_magnet"
    structured = output["structured_data"]
    for key in _STRUCTURED_KEYS:
        assert key in structured
        assert structured[key]
    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    assert (
        run_after["task_snapshots"][lead_index]["status"]
        == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
    )


@pytest.mark.asyncio
async def test_duplicate_lead_magnet_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.113 Lead magnet duplicate")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(
        db_session,
        owner_id,
        UUID(project_id),
        _PLAN_SPECIALISTS,
    )
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN_SPECIALISTS)
    lead_index = task_index_for(run, MarketingSpecialistType.LEAD_MAGNET_SPECIALIST)
    assert execute_specialist(client, auth_headers, project_id, run["id"], lead_index).status_code == 409


@pytest.mark.asyncio
async def test_lead_magnet_no_tools_or_content_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.113 Lead magnet safety")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(
        db_session,
        owner_id,
        UUID(project_id),
        _PLAN_SPECIALISTS,
    )
    run = start_run(client, auth_headers, project_id, plan_id)
    execute_through(client, auth_headers, project_id, run, _PLAN_SPECIALISTS)
    project_uuid = UUID(project_id)
    tool_count = (
        await db_session.execute(
            select(func.count())
            .select_from(ToolExecutionLogTable)
            .where(ToolExecutionLogTable.project_id == project_uuid),
        )
    ).scalar_one()
    assert tool_count == 0
    assets = await ContentAssetRepository(db_session).list_by_project(owner_id, project_uuid)
    assert assets == []
