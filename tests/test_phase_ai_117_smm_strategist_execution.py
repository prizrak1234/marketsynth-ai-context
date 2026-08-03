"""Phase AI.117 — SMM Strategist execution."""

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
    MarketingSpecialistType.CONTENT_PLANNER,
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.SMM_STRATEGIST,
]
_KEYS = (
    "platform_focus",
    "content_formats",
    "posting_frequency",
    "engagement_hooks",
    "community_management_notes",
    "social_proof_ideas",
    "risks",
)


@pytest.mark.asyncio
async def test_cannot_execute_smm_before_content_planner(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.117 SMM guard")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(
        client,
        auth_headers,
        project_id,
        run,
        [MarketingSpecialistType.STRATEGIST, MarketingSpecialistType.RESEARCHER],
    )
    response = execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        task_index_for(run, MarketingSpecialistType.SMM_STRATEGIST),
    )
    assert response.status_code == 409
    assert "Content Planner" in conflict_message(response)


@pytest.mark.asyncio
async def test_smm_executes_with_smm_strategy_output(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.117 SMM happy")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN[:-1])
    response = execute_specialist(
        client,
        auth_headers,
        project_id,
        run["id"],
        task_index_for(run, MarketingSpecialistType.SMM_STRATEGIST),
    )
    assert response.status_code == 201, response.text
    output = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs/{response.json()['specialist_output_id']}",
        headers=auth_headers,
    ).json()
    assert output["output_type"] == "smm_strategy"
    for key in _KEYS:
        assert output["structured_data"][key]


@pytest.mark.asyncio
async def test_duplicate_smm_execution_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = create_project(client, auth_headers, "AI.117 SMM duplicate")
    owner_id = await owner_id_for_project(db_session, project_id)
    plan_id = await create_approved_plan_with_specialists(db_session, owner_id, UUID(project_id), _PLAN)
    run = start_run(client, auth_headers, project_id, plan_id)
    run = execute_through(client, auth_headers, project_id, run, _PLAN)
    smm_index = task_index_for(run, MarketingSpecialistType.SMM_STRATEGIST)
    assert execute_specialist(client, auth_headers, project_id, run["id"], smm_index).status_code == 409
