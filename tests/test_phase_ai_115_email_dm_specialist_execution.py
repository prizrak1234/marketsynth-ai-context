"""Phase AI.115 — Email/DM Specialist execution."""

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
    MarketingSpecialistType.SALES_COPYWRITER,
    MarketingSpecialistType.EMAIL_DM_SPECIALIST,
]

_STRUCTURED_KEYS = (
    "sequence_steps",
    "message_goals",
    "cta_map",
    "trigger_points",
    "followup_rules",
)


@pytest.mark.asyncio
async def test_cannot_execute_email_dm_before_sales_copywriter(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.115 Email guard")
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
    email_index = task_index_for(run, MarketingSpecialistType.EMAIL_DM_SPECIALIST)
    response = execute_specialist(client, auth_headers, project_id, run["id"], email_index)
    assert response.status_code == 409
    assert "Sales Copywriter" in conflict_message(response)


@pytest.mark.asyncio
async def test_email_dm_executes_with_structured_output(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.115 Email happy")
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
    email_index = task_index_for(run, MarketingSpecialistType.EMAIL_DM_SPECIALIST)
    response = execute_specialist(client, auth_headers, project_id, run["id"], email_index)
    assert response.status_code == 201, response.text
    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{response.json()['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "email_sequence"
    structured = output["structured_data"]
    for key in _STRUCTURED_KEYS:
        assert key in structured
        assert structured[key]
    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    assert (
        run_after["task_snapshots"][email_index]["status"]
        == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
    )


@pytest.mark.asyncio
async def test_duplicate_email_dm_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.115 Email duplicate")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(
        db_session,
        owner_id,
        UUID(project_id),
        _PLAN_SPECIALISTS,
    )
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN_SPECIALISTS)
    email_index = task_index_for(run, MarketingSpecialistType.EMAIL_DM_SPECIALIST)
    assert execute_specialist(client, auth_headers, project_id, run["id"], email_index).status_code == 409


@pytest.mark.asyncio
async def test_email_dm_no_tools_or_content_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.115 Email safety")
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
