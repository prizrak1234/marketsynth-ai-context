"""RUNTIME-01F — public contract must not expose E2E deterministic controls."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app
from tests.conftest import _create_user_with_api_key
from tests.test_runtime_01a_biv_durable_lifecycle import _seed_biv_request


@pytest.fixture
def biv_runtime_01f_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUSINESS_IDEA_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("MCP_READ_ONLY_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "true")
    monkeypatch.setenv("BIV_RUN_DISPATCHER_ENABLED", "true")
    monkeypatch.setenv("BIV_E2E_DETERMINISTIC_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_runtime_01f_openapi_has_no_e2e_deterministic_controls() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200, resp.text
        spec = resp.text
        assert "e2e_deterministic_outcome" not in spec
        assert "BivE2eDeterministicOutcome" not in spec
        assert "e2e_deterministic_fixture" not in spec


@pytest.mark.asyncio
async def test_runtime_01f_post_runs_rejects_extra_test_outcome_field(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key, _user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        resp = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
            json={
                **seeded["run_body"],
                "e2e_deterministic_outcome": "verdict",
            },
            headers=headers,
        )
        assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_runtime_01f_sync_run_rejects_extra_test_outcome_field(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key, _user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        resp = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/run",
            json={
                **seeded["run_body"],
                "e2e_deterministic_outcome": "verdict",
            },
            headers=headers,
        )
        assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_runtime_01f_canonical_post_runs_accepts_production_shape(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key, _user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        resp = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
            json=seeded["run_body"],
            headers=headers,
        )
        assert resp.status_code == 202, resp.text
        assert "run_id" in resp.json()
