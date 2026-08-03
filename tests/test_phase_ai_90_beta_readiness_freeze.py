"""Phase AI.90 — Beta readiness freeze invariants."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from app.core.config import get_settings
from app.services.e2e_demo_seed_service import E2eDemoSeedService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_freeze_doc_exists() -> None:
    doc = Path("docs/phase_ai_90_beta_readiness_audit.md")
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "/me/onboarding" in text
    assert "rate_limit" in text.lower() or "429" in text
    assert "error_code" in text


def test_openapi_onboarding_and_beta_admin(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = " ".join(spec.get("paths", {}).keys())
    assert "/me/onboarding" in paths
    assert "/me/beta-admin/dashboard" in paths


@pytest.mark.asyncio
async def test_onboarding_derived_and_manual_demo(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    bootstrap = client.post("/projects", json={"name": "AI.90"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    seed = await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    status = client.get(
        f"/me/onboarding?project_id={seed.project_id}",
        headers=auth_headers,
    )
    assert status.status_code == 200, status.text
    body = status.json()
    steps = {item["step"]: item for item in body["steps"]}
    assert steps["project_created"]["completed"] is True
    assert steps["first_publication_job_created"]["completed"] is True
    assert steps["demo_seeded"]["manual_allowed"] is True

    manual = client.post(
        "/me/onboarding/complete-step",
        json={"step": "project_created"},
        headers=auth_headers,
    )
    assert manual.status_code == 409
    envelope = manual.json()
    assert "error_code" in envelope


def test_project_limit_returns_429_envelope(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BETA_LIMITS_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BETA_STRICT_MAX_PROJECTS_PER_USER", "1")
    get_settings.cache_clear()

    first = client.post("/projects", json={"name": "Limit A"}, headers=auth_headers)
    assert first.status_code == 201
    second = client.post("/projects", json={"name": "Limit B"}, headers=auth_headers)
    assert second.status_code == 429
    body = second.json()
    assert body["error_code"] == "project_limit_exceeded"
    assert "safe_message" in body
    assert "traceback" not in str(body).lower()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_beta_admin_dashboard_no_secrets(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    bootstrap = client.post("/projects", json={"name": "AI.90 admin"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    response = client.get("/me/beta-admin/dashboard", headers=auth_headers)
    assert response.status_code == 200, response.text
    blob = str(response.json()).lower()
    assert "bot_token" not in blob
    assert "payload_snapshot" not in blob
    assert "prompt" not in blob


@pytest.mark.asyncio
async def test_e2e_demo_still_works_after_beta_layer(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    bootstrap = client.post("/projects", json={"name": "AI.90 e2e"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    seed = await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    demo = client.get(
        f"/projects/{seed.project_id}/demo-flow/status",
        headers=auth_headers,
    )
    assert demo.status_code == 200
    assert demo.json()["publication_job_status"] == "queued"
