"""Phase AI.118 — Ad Creative Strategist execution."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.schemas.contracts import MarketingSpecialistType
from fastapi.testclient import TestClient
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

_PLAN = [
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.SALES_COPYWRITER,
    MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
]
_KEYS = (
    "creative_angles",
    "ad_hooks",
    "visual_concepts",
    "primary_text_variants",
    "headline_variants",
    "cta_variants",
    "testing_matrix",
)


@pytest.mark.asyncio
async def test_cannot_execute_ad_creative_before_sales_copywriter(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.118 Ad guard")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(
        client,
        auth_headers,
        project_id,
        run,
        _PLAN[:-2],
    )
    response = execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        task_index_for(run, MarketingSpecialistType.AD_CREATIVE_STRATEGIST),
    )
    assert response.status_code == 409
    assert "Sales Copywriter" in conflict_message(response)


@pytest.mark.asyncio
async def test_ad_creative_executes_with_ad_creative_strategy_output(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.118 Ad happy")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN[:-1])
    response = execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        task_index_for(run, MarketingSpecialistType.AD_CREATIVE_STRATEGIST),
    )
    assert response.status_code == 201, response.text
    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{response.json()['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "ad_creative_strategy"
    for key in _KEYS:
        assert output["structured_data"][key]


@pytest.mark.asyncio
async def test_duplicate_ad_creative_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.118 Ad duplicate")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN)
    ad_index = task_index_for(run, MarketingSpecialistType.AD_CREATIVE_STRATEGIST)
    assert execute_specialist(client, auth_headers, project_id, run["id"], ad_index).status_code == 409
