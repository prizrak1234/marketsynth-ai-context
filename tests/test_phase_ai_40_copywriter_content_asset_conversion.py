"""Phase AI.40 — Copywriter approved output → ContentAsset draft (explicit)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.repositories.content_assets import ContentAssetRepository
from app.marketing.contracts import ContentAssetStatus
from app.schemas.contracts import (
    ChatBlockActionType,
    MarketingSpecialistType,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.40 Asset"}, headers=headers)
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


def _approved_plan_id(client: TestClient, headers: dict[str, str], project_id: str) -> str:
    orchestrator_id = _create_agent(client, headers, project_id, agent_type="orchestrator")
    chat = client.post(
        f"/projects/{project_id}/agent-chat",
        json={"content": STRATEGY_MESSAGE, "agent_id": orchestrator_id},
        headers=headers,
    ).json()
    saved = client.post(
        f"/projects/{project_id}/agent-chat/block-actions",
        json={
            "session_id": chat["session_id"],
            "assistant_message_id": chat["assistant_message_id"],
            "block_index": 0,
            "action_type": ChatBlockActionType.SAVE_MARKETING_PLAN.value,
        },
        headers=headers,
    ).json()
    plan_id = saved["created_resource_id"]
    assert (
        client.post(
            f"/projects/{project_id}/marketing-plans/{plan_id}/approve",
            headers=headers,
        ).status_code
        == 200
    )
    return plan_id


def _start_run(client: TestClient, headers: dict[str, str], project_id: str, plan_id: str) -> dict:
    created = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}/start",
        headers=headers,
    )
    return client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{body['id']}",
        headers=headers,
    ).json()


def _task_index_for(run: dict, specialist: MarketingSpecialistType) -> int:
    return next(
        i for i, t in enumerate(run["task_snapshots"]) if t["specialist"] == specialist.value
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


def _execute_through_copywriter(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    plan_id: str,
) -> tuple[dict, dict]:
    run = _start_run(client, headers, project_id, plan_id)
    for specialist in (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
    ):
        idx = _task_index_for(run, specialist)
        assert _execute_specialist(client, headers, project_id, run["id"], idx).status_code == 201
    run = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run['id']}",
        headers=headers,
    ).json()
    copy_idx = _task_index_for(run, MarketingSpecialistType.COPYWRITER)
    outputs = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run["id"], "specialist": "copywriter"},
        headers=headers,
    ).json()
    assert outputs
    return run, outputs[0]


def _create_asset(client: TestClient, headers: dict[str, str], project_id: str, output_id: str):
    return client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output_id}/create-content-asset",
        headers=headers,
    )


def test_cannot_create_asset_from_draft_copywriter(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    _run, output = _execute_through_copywriter(client, auth_headers, project_id, plan_id)
    response = _create_asset(client, auth_headers, project_id, output["id"])
    assert response.status_code == 409
    assert "approved" in response.json()["detail"].lower()


def test_cannot_create_asset_from_non_copywriter(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run = _start_run(client, auth_headers, project_id, plan_id)
    idx = _task_index_for(run, MarketingSpecialistType.STRATEGIST)
    assert _execute_specialist(client, auth_headers, project_id, run["id"], idx).status_code == 201
    outputs = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run["id"], "specialist": "strategist"},
        headers=headers,
    ).json()
    approved = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{outputs[0]['id']}/approve",
        headers=headers,
    )
    assert approved.status_code == 200
    response = _create_asset(client, auth_headers, project_id, outputs[0]["id"])
    assert response.status_code == 409
    assert "copywriter" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_content_asset_from_approved_copywriter(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    run, output = _execute_through_copywriter(client, auth_headers, project_id, plan_id)

    approved = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200

    assets_before = await ContentAssetRepository(db_session).list_by_project(
        UUID(output["owner_id"]),
        UUID(project_id),
    )

    response = _create_asset(client, auth_headers, project_id, output["id"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["content_asset_status"] == ContentAssetStatus.DRAFT.value

    asset = client.get(
        f"/projects/{project_id}/content-assets/{body['content_asset_id']}",
        headers=auth_headers,
    ).json()
    assert asset["status"] == ContentAssetStatus.DRAFT.value
    assert asset["title"]
    assert asset["body"]
    assert str(asset["metadata"].get("conversion_source")) == "copywriter_specialist_output"

    owner_id = UUID(output["owner_id"])
    project_uuid = UUID(project_id)
    assets_after = await ContentAssetRepository(db_session).list_by_project(
        owner_id,
        project_uuid,
    )
    assert len(assets_after) == len(assets_before) + 1

    row = await ContentAssetRepository(db_session).get_by_id_for_owner(
        UUID(body["content_asset_id"]),
        owner_id,
        project_uuid,
    )
    assert row is not None
    assert row.source_marketing_plan_id == UUID(plan_id)
    assert row.source_execution_run_id == UUID(run["id"])
    assert row.source_specialist_output_id == UUID(output["id"])
    assert row.source_specialist_type == MarketingSpecialistType.COPYWRITER.value
    assert row.approved_version_number is None


def test_duplicate_create_content_asset_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    _run, output = _execute_through_copywriter(client, auth_headers, project_id, plan_id)
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
        headers=auth_headers,
    )
    first = _create_asset(client, auth_headers, project_id, output["id"])
    assert first.status_code == 201
    second = _create_asset(client, auth_headers, project_id, output["id"])
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_approve_copywriter_output_does_not_auto_create_asset(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    project_id = _create_project(client, auth_headers)
    plan_id = _approved_plan_id(client, auth_headers, project_id)
    _run, output = _execute_through_copywriter(client, auth_headers, project_id, plan_id)
    owner_id = UUID(output["owner_id"])
    before = await ContentAssetRepository(db_session).list_by_project(
        owner_id,
        UUID(project_id),
    )
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
        headers=auth_headers,
    )
    after = await ContentAssetRepository(db_session).list_by_project(owner_id, UUID(project_id))
    assert len(after) == len(before)
