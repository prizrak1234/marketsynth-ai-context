"""Phase AI.95 — Beta feedback + QA loop freeze invariants."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from app.services.e2e_demo_seed_service import E2eDemoSeedService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_freeze_doc_exists() -> None:
    doc = Path("docs/phase_ai_95_beta_qa_readiness_audit.md")
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "/me/beta-feedback" in text
    assert "/me/beta-admin/qa-export" in text
    assert "failed_step" in text
    assert "safe_context" in text


def test_openapi_beta_feedback_and_qa_export(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = " ".join(spec.get("paths", {}).keys())
    assert "/me/beta-feedback" in paths
    assert "/me/beta-admin/feedback" in paths
    assert "/me/beta-admin/qa-export" in paths


@pytest.mark.asyncio
async def test_feedback_create_list_archive(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    bootstrap = client.post("/projects", json={"name": "AI.95"}, headers=auth_headers)
    project_id = bootstrap.json()["id"]

    create = client.post(
        "/me/beta-feedback",
        json={
            "title": "Demo stuck",
            "description": "Cannot approve package on step 7",
            "project_id": project_id,
            "source": "publishing",
            "severity": "high",
            "safe_context": {
                "step": "publishing",
                "error_code": "gate_blocked",
                "api_key": "must-not-persist",
                "payload_snapshot": {"secret": "x"},
            },
        },
        headers=auth_headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    report_id = body["id"]
    assert body["status"] == "open"
    assert "api_key" not in body["safe_context"]
    assert "payload_snapshot" not in body["safe_context"]
    assert body["safe_context"].get("error_code") == "gate_blocked"

    listed = client.get("/me/beta-feedback", headers=auth_headers)
    assert listed.status_code == 200
    assert any(item["id"] == report_id for item in listed.json())

    detail = client.get(f"/me/beta-feedback/{report_id}", headers=auth_headers)
    assert detail.status_code == 200

    archived = client.post(
        f"/me/beta-feedback/{report_id}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_admin_triage_resolve_and_qa_export_safe(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    bootstrap = client.post("/projects", json={"name": "AI.95 admin"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    project_id = bootstrap.json()["id"]
    await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    create = client.post(
        "/me/beta-feedback",
        json={
            "title": "Blocker on publish",
            "description": "Job stays failed after dry run",
            "project_id": project_id,
            "severity": "blocker",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    report_id = create.json()["id"]

    triage = client.post(
        f"/me/beta-admin/feedback/{report_id}/triage",
        headers=auth_headers,
    )
    assert triage.status_code == 200, triage.text
    assert triage.json()["status"] == "triaged"

    resolve = client.post(
        f"/me/beta-admin/feedback/{report_id}/resolve",
        headers=auth_headers,
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved"

    export = client.get("/me/beta-admin/qa-export", headers=auth_headers)
    assert export.status_code == 200, export.text
    blob = json.dumps(export.json()).lower()
    assert "bot_token" not in blob
    assert "prompt" not in blob
    assert "payload_snapshot" not in blob
    assert "description" not in blob
    assert export.json()["feedback_counts"]["resolved"] >= 1


@pytest.mark.asyncio
async def test_demo_flow_failure_markers_no_raw_errors(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    bootstrap = client.post("/projects", json={"name": "AI.95 demo"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    seed = await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    response = client.get(
        f"/projects/{seed.project_id}/demo-flow/status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "failed_step" in body
    assert "blocking_reason" in body
    assert "last_error_code" in body
    assert "suggested_next_action" in body
    blob = str(body).lower()
    assert "traceback" not in blob
    assert "stack" not in blob or body.get("failed_step") is not None


def test_ai_90_regression_still_importable() -> None:
    import tests.test_phase_ai_90_beta_readiness_freeze as ai90

    assert hasattr(ai90, "test_freeze_doc_exists")
