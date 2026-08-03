"""Phase AI.123 — Marketing department v2 regression smoke."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.tool_execution_log import ToolExecutionLogTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.schemas.contracts import (
    MarketingPlanExecutionTaskStatus,
    MarketingSpecialistType,
)
from app.services.agent_runs import AgentRunService
from app.services.marketing_pipeline_execution_service import MarketingPipelineExecutionService
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.v2_specialist_execution_helpers import (
    V2_REGRESSION_SPECIALISTS,
    create_approved_plan_with_specialists,
    create_project,
    execute_through,
    owner_id_for_project,
    start_run,
    task_index_for,
)

V2_OUTPUT_TYPES: dict[MarketingSpecialistType, str] = {
    MarketingSpecialistType.OFFER_STRATEGIST: "offer_strategy",
    MarketingSpecialistType.FUNNEL_ARCHITECT: "funnel_design",
    MarketingSpecialistType.LEAD_MAGNET_SPECIALIST: "lead_magnet",
    MarketingSpecialistType.SALES_COPYWRITER: "sales_copy",
    MarketingSpecialistType.EMAIL_DM_SPECIALIST: "email_sequence",
    MarketingSpecialistType.CRO_SPECIALIST: "cro_recommendations",
    MarketingSpecialistType.SMM_STRATEGIST: "smm_strategy",
    MarketingSpecialistType.AD_CREATIVE_STRATEGIST: "ad_creative_strategy",
}


@pytest.mark.asyncio
async def test_v2_regression_executes_all_enabled_roles_in_order(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.123 v2 regression")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(
        db_session,
        owner_id,
        UUID(project_id),
        V2_REGRESSION_SPECIALISTS,
    )
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, V2_REGRESSION_SPECIALISTS)
    project_uuid = UUID(project_id)

    for specialist, expected_type in V2_OUTPUT_TYPES.items():
        index = task_index_for(run, specialist)
        task = run["task_snapshots"][index]
        assert task["status"] == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
        assert task["output_ref"]
        output = client.get(
            f"/projects/{project_id}/marketing-specialist-outputs/{task['output_ref']}",
            headers=auth_headers,
        ).json()
        assert output["output_type"] == expected_type
        assert output["current_version_number"] == 1
        assert output["status"] == "draft"

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


def test_frozen_six_pipeline_order_regression() -> None:
    assert MarketingPipelineExecutionService.pipeline_order() == [
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
        MarketingSpecialistType.CRITIC,
        MarketingSpecialistType.ANALYST,
    ]
