"""Phase AI.111 — Offer Strategist specialist execution."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.llm import LLMRequestTable
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
]

_STRUCTURED_KEYS = (
    "core_offer",
    "value_proposition",
    "unique_mechanism",
    "offer_variants",
    "pricing_hypotheses",
    "risk_reversal",
    "positioning_statement",
)


@pytest.mark.asyncio
async def test_cannot_execute_offer_strategist_before_researcher(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.111 Offer guard")
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
        [MarketingSpecialistType.STRATEGIST],
    )
    offer_index = task_index_for(run, MarketingSpecialistType.OFFER_STRATEGIST)
    response = execute_specialist(client, auth_headers, project_id, run["id"], offer_index)
    assert response.status_code == 409
    assert "Researcher" in conflict_message(response)


@pytest.mark.asyncio
async def test_offer_strategist_executes_with_structured_output(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.111 Offer happy")
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
        [
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
        ],
    )
    offer_index = task_index_for(run, MarketingSpecialistType.OFFER_STRATEGIST)
    response = execute_specialist(client, auth_headers, project_id, run["id"], offer_index)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["specialist"] == MarketingSpecialistType.OFFER_STRATEGIST.value

    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{body['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "offer_strategy"
    structured = output["structured_data"]
    for key in _STRUCTURED_KEYS:
        assert key in structured
        assert structured[key]
    assert structured.get("mock") is True

    run_after = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=auth_headers,
    ).json()
    task = run_after["task_snapshots"][offer_index]
    assert task["status"] == MarketingPlanExecutionTaskStatus.SPECIALIST_COMPLETED.value
    assert task["output_ref"] == body["specialist_output_id"]


@pytest.mark.asyncio
async def test_duplicate_offer_strategist_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.111 Offer duplicate")
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
        _PLAN_SPECIALISTS,
    )
    offer_index = task_index_for(run, MarketingSpecialistType.OFFER_STRATEGIST)
    second = execute_specialist(client, auth_headers, project_id, run["id"], offer_index)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_offer_strategist_no_tools_child_runs_or_content_assets(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.111 Offer safety")
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
        _PLAN_SPECIALISTS,
    )
    output_id = run["task_snapshots"][
        task_index_for(run, MarketingSpecialistType.OFFER_STRATEGIST)
    ]["output_ref"]
    project_uuid = UUID(project_id)
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
        assert meta.get("tools_metadata") is None or meta.get("tools_metadata", {}).get(
            "available_tool_names",
        ) in (None, [])

    assets_before = await ContentAssetRepository(db_session).list_by_project(owner_id, project_uuid)
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output_id}/approve",
        headers=auth_headers,
    )
    assets_after = await ContentAssetRepository(db_session).list_by_project(owner_id, project_uuid)
    assert len(assets_after) == len(assets_before)
