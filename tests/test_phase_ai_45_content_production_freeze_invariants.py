"""Phase AI.45 — Content production layer freeze invariants (AI.40–AI.44)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.db.models.publishing import PublicationJobTable
from app.db.repositories.content_assets import ContentAssetRepository
from app.db.repositories.publication_packages import PublicationPackageRepository
from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.schemas.contracts import (
    ChatBlockActionType,
    MarketingSpecialistType,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

STRATEGY_MESSAGE = "Сделай контент-стратегию для стоматологии"


def _create_project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "AI.45 Freeze"}, headers=headers)
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


def _approved_plan_and_copywriter_output(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
) -> tuple[str, dict]:
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
    client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/approve",
        headers=headers,
    )
    run_created = client.post(
        f"/projects/{project_id}/marketing-plans/{plan_id}/execution-runs",
        headers=headers,
    ).json()
    run_id = run_created["id"]
    client.post(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}/start",
        headers=headers,
    )
    run = client.get(
        f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}",
        headers=headers,
    ).json()
    for specialist in (
        MarketingSpecialistType.STRATEGIST,
        MarketingSpecialistType.RESEARCHER,
        MarketingSpecialistType.CONTENT_PLANNER,
        MarketingSpecialistType.COPYWRITER,
    ):
        idx = next(
            i for i, t in enumerate(run["task_snapshots"]) if t["specialist"] == specialist.value
        )
        client.post(
            f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}/tasks/{idx}/execute-specialist",
            headers=headers,
        )
        run = client.get(
            f"/projects/{project_id}/marketing-plan-execution-runs/{run_id}",
            headers=headers,
        ).json()
    outputs = client.get(
        f"/projects/{project_id}/marketing-specialist-outputs",
        params={"execution_run_id": run_id, "specialist": "copywriter"},
        headers=headers,
    ).json()
    return plan_id, outputs[0]


@pytest.mark.asyncio
async def test_full_content_production_chain_no_auto_publish(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Copywriter → asset → review → approved → package; no jobs or outbound send."""
    project_id = _create_project(client, auth_headers)
    _plan_id, output = _approved_plan_and_copywriter_output(client, auth_headers, project_id)
    client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/approve",
        headers=auth_headers,
    )

    asset_resp = client.post(
        f"/projects/{project_id}/marketing-specialist-outputs/{output['id']}/create-content-asset",
        headers=auth_headers,
    )
    assert asset_resp.status_code == 201
    asset_id = asset_resp.json()["content_asset_id"]

    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/submit-review",
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/approve",
        headers=auth_headers,
    )
    pkg_resp = client.post(
        f"/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        json={"channel": "telegram"},
        headers=auth_headers,
    )
    assert pkg_resp.status_code == 201

    owner_id = UUID(output["owner_id"])
    project_uuid = UUID(project_id)

    asset_row = await ContentAssetRepository(db_session).get_by_id_for_owner(
        UUID(asset_id),
        owner_id,
        project_uuid,
    )
    assert asset_row is not None
    assert asset_row.status == ContentAssetStatus.APPROVED
    assert asset_row.submitted_for_review_at is not None
    assert asset_row.approved_at is not None

    packages = await PublicationPackageRepository(db_session).list_by_project(
        owner_id,
        project_uuid,
        content_asset_id=UUID(asset_id),
    )
    assert len(packages) == 1
    assert packages[0].status == PublicationPackageStatus.DRAFT

    job_count = (
        await db_session.execute(
            select(func.count())
            .select_from(PublicationJobTable)
            .where(PublicationJobTable.project_id == project_uuid),
        )
    ).scalar_one()
    assert job_count == 0


def test_no_publish_endpoints_on_content_production_routes(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """OpenAPI must not expose send/publish on new content-production paths."""
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})
    watched_prefixes = (
        "/projects/{project_id}/content-assets/{asset_id}/create-publication-package",
        "/projects/{project_id}/publication-packages",
    )
    forbidden_suffixes = ("/publish", "/send", "/schedule")
    for path_key, methods in paths.items():
        if not any(prefix in path_key for prefix in watched_prefixes):
            continue
        for method, operation in methods.items():
            if method.startswith("x-"):
                continue
            operation_id = (operation.get("operationId") or "").lower()
            summary = (operation.get("summary") or "").lower()
            for suffix in forbidden_suffixes:
                assert suffix not in path_key, path_key
                assert suffix not in operation_id, operation_id
                assert "publish" not in summary or "package" in summary, summary
