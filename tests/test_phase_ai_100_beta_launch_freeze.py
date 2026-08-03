"""Phase AI.100 — Beta launch pack freeze invariants."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import UUID

import pytest
from app.core.config import get_settings
from app.schemas.contracts import BetaAccessStatus, UserRole
from app.schemas.crud import UserUpdate
from app.services.e2e_demo_seed_service import E2eDemoSeedService
from app.services.users_service import UserService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_freeze_doc_exists() -> None:
    doc = Path("docs/phase_ai_100_beta_launch_readiness_audit.md")
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "/me/beta-access" in text
    assert "/me/beta-guide" in text
    assert "smoke_beta_launch.py" in text
    assert "rollback" in text.lower()


def test_openapi_beta_launch_endpoints(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = " ".join(spec.get("paths", {}).keys())
    assert "/me/beta-access" in paths
    assert "/me/beta-guide" in paths
    assert "/me/beta-admin/users/{user_id}/approve-beta" in paths
    assert "/projects/{project_id}/demo-flow/reset" in paths


def test_beta_guide_safe(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/me/beta-guide", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["current_phase"]
    assert len(body["expected_path"]) >= 5
    blob = str(body).lower()
    assert "bot_token" not in blob
    assert "api_key" not in blob


@pytest.mark.asyncio
async def test_beta_access_pending_blocks_mvp(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BETA_ACCESS_GATE_ENABLED", "true")
    get_settings.cache_clear()

    bootstrap = client.post("/projects", json={"name": "gate"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    await UserService(db_session).update(
        owner_id,
        UserUpdate(beta_access_status=BetaAccessStatus.PENDING),
    )
    await db_session.commit()

    blocked = client.get("/me/onboarding", headers=auth_headers)
    assert blocked.status_code == 403
    assert blocked.json()["error_code"] == "beta_access_pending"

    access = client.get("/me/beta-access", headers=auth_headers)
    assert access.status_code == 200
    assert access.json()["can_use_mvp"] is False

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_admin_approve_beta_unblocks(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BETA_ACCESS_GATE_ENABLED", "true")
    monkeypatch.setenv("BETA_ADMIN_ENDPOINTS_ENABLED", "true")
    get_settings.cache_clear()

    bootstrap = client.post("/projects", json={"name": "approve"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    await UserService(db_session).update(
        owner_id,
        UserUpdate(
            beta_access_status=BetaAccessStatus.PENDING,
            role=UserRole.OWNER,
        ),
    )
    await db_session.commit()

    approved = client.post(
        f"/me/beta-admin/users/{owner_id}/approve-beta",
        json={"notes": "invited"},
        headers=auth_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["beta_access_status"] == "approved"

    onboarding = client.get("/me/onboarding", headers=auth_headers)
    assert onboarding.status_code == 200

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_demo_reset_dev_admin(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    bootstrap = client.post("/projects", json={"name": "reset"}, headers=auth_headers)
    owner_id = UUID(bootstrap.json()["owner_id"])
    seed = await E2eDemoSeedService(db_session).seed(owner_id=owner_id)
    await db_session.commit()

    first = client.post(
        f"/projects/{seed.project_id}/demo-flow/reset",
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["cleared"] is True

    second = client.post(
        f"/projects/{seed.project_id}/demo-flow/reset",
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert second.json()["cleared"] is False


def test_smoke_script_importable() -> None:
    path = Path("scripts/smoke_beta_launch.py")
    assert path.is_file()
    spec = importlib.util.spec_from_file_location("smoke_beta_launch", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "main")


def test_ai_95_regression_still_importable() -> None:
    import tests.test_phase_ai_95_beta_qa_readiness_freeze as ai95

    assert hasattr(ai95, "test_freeze_doc_exists")
