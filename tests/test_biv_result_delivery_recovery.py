"""PRODUCT-01.3B — BIV result delivery through project hydration (latest-run/latest)."""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from app.business_idea_validation.e2e_deterministic_fixture import (
    E2eDeterministicFixtureService,
    E2eDeterministicOutcome,
)
from app.business_idea_validation.skill import BusinessIdeaValidationSkill
from app.core.config import get_settings
from app.core.exceptions import InvalidStateError
from app.db.session import get_session_factory
from app.main import app
from app.schemas.contracts import (
    BusinessIdeaValidationRunStatus,
    BusinessIdeaValidationVerdictKind,
)
from httpx import ASGITransport, AsyncClient
from tests.conftest import _create_user_with_api_key
from tests.test_cwf_1a_launch_pack_decision import _output
from tests.test_runtime_01a_biv_durable_lifecycle import _seed_biv_request

pytestmark = pytest.mark.usefixtures("biv_runtime_env")


@pytest.fixture
def biv_e2e_deterministic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIV_E2E_DETERMINISTIC_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()


async def _bind_partial_fixture(db_session, owner_id: UUID) -> None:
    svc = E2eDeterministicFixtureService(db_session, get_settings())
    await svc.bind_for_owner(
        owner_id,
        E2eDeterministicOutcome.PARTIAL,
        e2e_run_id="delivery-recovery-partial",
    )
    await db_session.commit()


async def _wait_run_terminal(
    client: AsyncClient,
    headers: dict[str, str],
    request_id: str,
    run_id: UUID,
    *,
    expect_status: str,
    max_ticks: int = 120,
) -> dict:
    for _ in range(max_ticks):
        get_run = await client.get(
            f"/user-requests/{request_id}/business-idea-validation/runs/{run_id}",
            headers=headers,
        )
        assert get_run.status_code == 200, get_run.text
        body = get_run.json()
        if body["status"] == expect_status:
            return body
        await asyncio.sleep(0.05)
    raise AssertionError(f"run {run_id} did not reach status {expect_status}")


@pytest.mark.asyncio
async def test_latest_run_returns_partial_research(
    db_session,
    biv_e2e_deterministic_env,
) -> None:
    api_key, user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        await _bind_partial_fixture(db_session, user.id)
        resp = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
            json=seeded["run_body"],
            headers=headers,
        )
        assert resp.status_code == 202
        run_id = UUID(resp.json()["run_id"])
        await _wait_run_terminal(
            client,
            headers,
            seeded["request_id"],
            run_id,
            expect_status="failed",
        )

        latest_run = await client.get(
            f"/projects/{seeded['project_id']}/business-idea-validation/latest-run",
            headers=headers,
        )
        assert latest_run.status_code == 200, latest_run.text
        body = latest_run.json()
        assert body["run_id"] == str(run_id)
        assert body["status"] == "failed"
        assert body["has_output"] is True
        assert body["result_kind"] == "partial_research"
        assert body["safe_error_code"] == "high_impact_insufficient_sources"
        assert body["research_terminal_state"] == "succeeded_insufficient"

        latest = await client.get(
            f"/projects/{seeded['project_id']}/business-idea-validation/latest",
            headers=headers,
        )
        assert latest.status_code == 200, latest.text
        hydration = latest.json()
        assert hydration["run_id"] == str(run_id)
        assert hydration["status"] == "failed"
        assert hydration["output"]["result_kind"] == "partial_research"
        assert hydration["output"]["verdict"] == "insufficient_evidence"
        assert hydration["output"]["customer_report"] is None


@pytest.mark.asyncio
async def test_latest_run_returns_succeeded(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fast_run(self, inp, **kwargs):
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", fast_run)

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
        assert resp.status_code == 202
        run_id = UUID(resp.json()["run_id"])
        await _wait_run_terminal(
            client,
            headers,
            seeded["request_id"],
            run_id,
            expect_status="succeeded",
        )

        latest_run = await client.get(
            f"/projects/{seeded['project_id']}/business-idea-validation/latest-run",
            headers=headers,
        )
        assert latest_run.status_code == 200
        body = latest_run.json()
        assert body["status"] == "succeeded"
        assert body["has_output"] is True


@pytest.mark.asyncio
async def test_latest_run_returns_running(db_session) -> None:
    gate = asyncio.Event()

    async def slow_run(self, inp, **kwargs):
        await gate.wait()
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    import app.business_idea_validation.skill as skill_mod

    original = skill_mod.BusinessIdeaValidationSkill.run
    skill_mod.BusinessIdeaValidationSkill.run = slow_run

    api_key, _user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            seeded = await _seed_biv_request(client, headers)
            resp = await client.post(
                f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
                json=seeded["run_body"],
                headers=headers,
            )
            assert resp.status_code == 202
            run_id = resp.json()["run_id"]

            latest_run = await client.get(
                f"/projects/{seeded['project_id']}/business-idea-validation/latest-run",
                headers=headers,
            )
            assert latest_run.status_code == 200, latest_run.text
            body = latest_run.json()
            assert body["run_id"] == run_id
            assert body["status"] in {"queued", "running"}
    finally:
        gate.set()
        skill_mod.BusinessIdeaValidationSkill.run = original


@pytest.mark.asyncio
async def test_latest_run_project_without_run_returns_404(db_session) -> None:
    api_key, _user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from tests.test_runtime_01a_biv_durable_lifecycle import IDEA

        project = await client.post(
            "/projects",
            json={"name": "Empty BIV project", "description": IDEA[:80]},
            headers=headers,
        )
        assert project.status_code == 201
        project_id = project.json()["id"]

        latest_run = await client.get(
            f"/projects/{project_id}/business-idea-validation/latest-run",
            headers=headers,
        )
        assert latest_run.status_code == 404

        latest = await client.get(
            f"/projects/{project_id}/business-idea-validation/latest",
            headers=headers,
        )
        assert latest.status_code == 404


@pytest.mark.asyncio
async def test_latest_run_status_query_uses_varchar_strings(db_session) -> None:
    """Regression: status column stores lowercase string values."""
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                __import__("sqlalchemy").text(
                    "SELECT DISTINCT status FROM business_idea_validation_runs LIMIT 20"
                )
            )
        ).scalars().all()
    for value in rows:
        assert isinstance(value, str)
        assert value in {
            BusinessIdeaValidationRunStatus.PENDING.value,
            BusinessIdeaValidationRunStatus.QUEUED.value,
            BusinessIdeaValidationRunStatus.RUNNING.value,
            BusinessIdeaValidationRunStatus.SUCCEEDED.value,
            BusinessIdeaValidationRunStatus.FAILED.value,
        }


@pytest.mark.asyncio
async def test_latest_run_technical_failure_without_output(db_session) -> None:
    async def boom_run(self, inp, **kwargs):
        raise InvalidStateError("investigation_immutable")

    import app.business_idea_validation.skill as skill_mod

    original = skill_mod.BusinessIdeaValidationSkill.run
    skill_mod.BusinessIdeaValidationSkill.run = boom_run

    api_key, _user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            seeded = await _seed_biv_request(client, headers)
            resp = await client.post(
                f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
                json=seeded["run_body"],
                headers=headers,
            )
            run_id = UUID(resp.json()["run_id"])
            await _wait_run_terminal(
                client,
                headers,
                seeded["request_id"],
                run_id,
                expect_status="failed",
            )

            latest_run = await client.get(
                f"/projects/{seeded['project_id']}/business-idea-validation/latest-run",
                headers=headers,
            )
            assert latest_run.status_code == 200
            body = latest_run.json()
            assert body["has_output"] is False
            assert body["result_kind"] is None
    finally:
        skill_mod.BusinessIdeaValidationSkill.run = original
