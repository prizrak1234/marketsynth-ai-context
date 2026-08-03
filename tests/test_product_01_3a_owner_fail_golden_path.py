"""PRODUCT-01.3A-OWNER-FAIL-01/02 — brief submit golden path backend chain."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.services.business_idea_validation_service import build_research_idempotency_key
from tests.conftest import _create_user_with_api_key
from tests.test_product_01_3a_biv_intake_gate import _valid_fields

pytest_plugins = ["tests.test_product_01_3a_backend_availability"]


def test_golden_path_confirm_then_run_creates_biv_run(
    migrated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirror frontend golden path: project → context → confirm → BIV run."""
    from app.business_idea_validation import skill as skill_mod
    from app.schemas.contracts import BivResearchTerminalState, BusinessIdeaValidationVerdictKind
    from tests.test_cwf_1a_launch_pack_decision import _output

    async def fake_skill_run(_self, _inp, **kwargs):
        output = _output(
            BusinessIdeaValidationVerdictKind.PROCEED,
            research_terminal_state=BivResearchTerminalState.SUCCEEDED_COMPLETE,
        )
        if kwargs.get("run_id"):
            output = output.model_copy(update={"run_id": str(kwargs["run_id"])})
        return output

    monkeypatch.setattr(skill_mod.BusinessIdeaValidationSkill, "run", fake_skill_run)

    plain_key, _user = asyncio.run(_create_user_with_api_key())
    headers = {"Authorization": f"Bearer {plain_key}"}
    fields = _valid_fields()

    project = migrated_client.post("/projects", headers=headers, json={"name": "Golden path project"})
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    draft = migrated_client.post(
        f"/projects/{project_id}/analysis-contexts",
        headers=headers,
        json=fields.model_dump(),
    )
    assert draft.status_code == 201, draft.text
    context_id = draft.json()["context_id"]
    snapshot = draft.json()["input_snapshot_hash"]
    assert snapshot

    confirm = migrated_client.post(
        f"/projects/{project_id}/analysis-contexts/{context_id}/confirm",
        headers=headers,
        json={},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["confirmed_by_user"] is True

    user_request = migrated_client.post(
        "/user-requests",
        headers=headers,
        json={
            "text": fields.idea_description,
            "selected_scenario": "idea_validation",
            "source": "home_conversation",
            "skill_inputs": {
                "home_agency_flow": "v2",
                "analysis_intent": "business_viability_research",
                "analysis_context_id": context_id,
            },
        },
    )
    assert user_request.status_code == 201, user_request.text
    user_request_id = user_request.json()["id"]

    run = migrated_client.post(
        f"/user-requests/{user_request_id}/business-idea-validation/run",
        headers=headers,
        json={
            "idempotency_key": build_research_idempotency_key(context_id, snapshot),
            "analysis_context_id": context_id,
            "input_snapshot_hash": snapshot,
            "idea": fields.idea_description,
        },
    )
    assert run.status_code in (200, 201), run.text
    body = run.json()
    assert body.get("run_id")
    assert body.get("project_id") == project_id

    fetched = migrated_client.get(f"/projects/{project_id}", headers=headers)
    assert fetched.status_code == 200, fetched.text


def test_reconcile_project_by_config_pointer(migrated_client: TestClient) -> None:
    """Frontend tryReconcileByDraftId must find project via marketsynth_i2 pointer."""
    plain_key, _user = asyncio.run(_create_user_with_api_key())
    headers = {"Authorization": f"Bearer {plain_key}"}
    local_draft_id = "draft_reconcile_pointer_test"

    created = migrated_client.post(
        "/projects",
        headers=headers,
        json={"name": "Reconcile pointer project", "description": "intake reconcile test"},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    updated = migrated_client.patch(
        f"/projects/{project_id}",
        headers=headers,
        json={
            "config": {
                "marketsynth_i2": {
                    "localDraftId": local_draft_id,
                    "submissionFingerprint": "fp_reconcile_test",
                    "localDraftVersion": "2026-01-01T00:00:00.000Z",
                }
            }
        },
    )
    assert updated.status_code == 200, updated.text

    listed = migrated_client.get("/projects", headers=headers)
    assert listed.status_code == 200, listed.text
    found = None
    for project in listed.json():
        cfg = project.get("config") or {}
        pointer = cfg.get("marketsynth_i2") or {}
        if pointer.get("localDraftId") == local_draft_id:
            found = project
            break
    assert found is not None
    assert found["id"] == project_id


def test_stale_project_id_does_not_block_new_create(migrated_client: TestClient) -> None:
    """Stale UUID must not terminal-fail; create a new project when reconcile misses."""
    plain_key, _user = asyncio.run(_create_user_with_api_key())
    headers = {"Authorization": f"Bearer {plain_key}"}
    stale_id = str(uuid.uuid4())

    stale_get = migrated_client.get(f"/projects/{stale_id}", headers=headers)
    assert stale_get.status_code == 404

    created = migrated_client.post(
        "/projects",
        headers=headers,
        json={"name": "Fresh after stale", "description": "localDraftId=draft_stale_test"},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    fetched = migrated_client.get(f"/projects/{project_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == project_id


def test_draft_local_id_is_not_backend_project(migrated_client: TestClient) -> None:
    plain_key, _user = asyncio.run(_create_user_with_api_key())
    headers = {"Authorization": f"Bearer {plain_key}"}
    resp = migrated_client.get("/projects/draft_abc123", headers=headers)
    assert resp.status_code in {404, 422}
