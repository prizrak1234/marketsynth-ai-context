"""Phase AI.174 — Campaign action center regression."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.marketing.scenario_wizard_steps import SCENARIO_WIZARD_STEPS
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from app.schemas.contracts import (
    CampaignActionResultStatus,
    CampaignActionType,
    CampaignHealthStatus,
    CampaignNextActionType,
)
from fastapi.testclient import TestClient
from tests.helpers.v2_specialist_execution_helpers import create_project


def conflict_message(response) -> str:
    body = response.json()
    return str(body.get("safe_message") or body.get("detail") or body)


def execute_action(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    campaign_id: str,
    action_type: str,
    *,
    idempotency_key: str | None = None,
):
    request_headers = dict(headers)
    if idempotency_key:
        request_headers["Idempotency-Key"] = idempotency_key
    return client.post(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/actions/{action_type}/execute",
        headers=request_headers,
    )


def test_control_center_exposes_primary_and_available_actions(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.174 actions list")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Action buttons",
            "goal": "Expose actions",
            "scenario_id": "dental_clinic_lead_gen",
        },
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert center.status_code == 200
    body = center.json()
    assert body["primary_action"] is not None
    assert body["primary_action"]["type"] == CampaignActionType.START_WIZARD.value
    assert body["primary_action"]["enabled"] is True
    assert any(
        action["type"] == CampaignActionType.START_WIZARD.value
        for action in body["available_actions"]
    )


def test_start_wizard_action_creates_wizard_run(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.174 start wizard action")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Start via action",
            "goal": "Wizard from button",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    result = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.START_WIZARD.value,
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == CampaignActionResultStatus.SUCCEEDED.value
    assert body["created_resource_type"] == "scenario_wizard_run"
    assert body["control_center_snapshot"]["next_action"]["action_type"] == (
        CampaignNextActionType.ADVANCE_WIZARD.value
    )


def test_dental_campaign_full_wizard_via_action_buttons_to_queued_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.174 dental action wizard")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Dental via actions",
            "goal": "Full pipeline from action center",
            "scenario_id": "dental_clinic_lead_gen",
        },
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]

    started = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.START_WIZARD.value,
    )
    assert started.status_code == 200, started.text

    for _ in range(len(SCENARIO_WIZARD_STEPS) + 2):
        center = client.get(
            f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
            headers=auth_headers,
        )
        assert center.status_code == 200
        snapshot = center.json()
        if snapshot["health"]["status"] == CampaignHealthStatus.COMPLETED.value:
            break
        primary = snapshot["primary_action"]
        assert primary is not None and primary["enabled"], snapshot
        advanced = execute_action(
            client,
            auth_headers,
            project_id,
            campaign_id,
            primary["type"],
        )
        assert advanced.status_code == 200, advanced.text

    final_center = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}/control-center",
        headers=auth_headers,
    )
    assert final_center.status_code == 200
    final = final_center.json()
    assert final["health"]["status"] == CampaignHealthStatus.COMPLETED.value
    assert final["metrics"]["jobs_total"] >= 1
    job_id = final["resource_ids"]["publication_package_job_id"]
    assert job_id
    job = client.get(
        f"/projects/{project_id}/publication-package-jobs/{job_id}",
        headers=auth_headers,
    )
    assert job.status_code == 200
    assert job.json()["status"] == PublicationPackageJobStatus.QUEUED.value


def test_unavailable_action_returns_conflict(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.174 action conflict")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Conflict test",
            "goal": "Bad action",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    bad = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.APPROVE_PLAN.value,
    )
    assert bad.status_code == 409


def test_idempotency_key_stores_replay_and_replays_on_same_state(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.174 idempotency")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Idempotent",
            "goal": "Replay",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    key = f"campaign-action-{uuid4()}"
    first = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.START_WIZARD.value,
        idempotency_key=key,
    )
    assert first.status_code == 200
    campaign = client.get(
        f"/projects/{project_id}/business-campaigns/{campaign_id}",
        headers=auth_headers,
    )
    assert campaign.status_code == 200
    assert "action_replay_cache" in (campaign.json().get("metadata") or {})


@pytest.mark.asyncio
async def test_idempotency_lookup_replays_matching_fingerprint() -> None:
    from uuid import uuid4

    from app.schemas.contracts import CampaignNextAction, CampaignNextActionType
    from app.services.campaign_action_idempotency import (
        build_state_fingerprint,
        lookup_replay,
        store_replay,
    )

    metadata: dict = {}
    fingerprint = build_state_fingerprint(["campaign", "start_wizard"])
    result = {
        "status": "succeeded",
        "message": "ok",
        "action_type": "start_wizard",
        "created_resource_type": "scenario_wizard_run",
        "created_resource_id": str(uuid4()),
        "updated_resource_type": None,
        "updated_resource_id": None,
        "next_action_after": CampaignNextAction(
            action_type=CampaignNextActionType.ADVANCE_WIZARD,
            label="Advance",
            safe_description="Advance wizard",
        ).model_dump(mode="json"),
        "control_center_snapshot": None,
    }
    from app.schemas.contracts import CampaignActionResult

    stored = CampaignActionResult.model_validate(result)
    metadata = store_replay(
        metadata,
        key_hash="abc123",
        state_fingerprint=fingerprint,
        result=stored,
    )
    replayed = lookup_replay(metadata, key_hash="abc123", state_fingerprint=fingerprint)
    assert replayed is not None
    assert replayed.message == "ok"


def test_idempotency_conflict_when_state_changed(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.174 idempotency conflict")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Idempotency conflict",
            "goal": "State change",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    key = f"campaign-action-conflict-{uuid4()}"
    first = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.START_WIZARD.value,
        idempotency_key=key,
    )
    assert first.status_code == 200
    execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.ADVANCE_WIZARD.value,
    )
    conflict = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.START_WIZARD.value,
        idempotency_key=key,
    )
    assert conflict.status_code == 409
    assert "idempotency" in conflict_message(conflict).lower()


def test_action_result_includes_next_action_after(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = create_project(client, auth_headers, "AI.174 next action after")
    created = client.post(
        f"/projects/{project_id}/business-campaigns",
        json={
            "name": "Next after",
            "goal": "Result contract",
            "scenario_id": "local_service_promo",
        },
        headers=auth_headers,
    )
    campaign_id = created.json()["id"]
    result = execute_action(
        client,
        auth_headers,
        project_id,
        campaign_id,
        CampaignActionType.START_WIZARD.value,
    )
    assert result.status_code == 200
    body = result.json()
    assert body["next_action_after"]["action_type"] == CampaignNextActionType.ADVANCE_WIZARD.value
    assert body["control_center_snapshot"] is not None
