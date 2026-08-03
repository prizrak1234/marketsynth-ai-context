"""RUNTIME-01F — canonical golden path backend: server-side fixture + ownership."""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.business_idea_validation.e2e_deterministic_fixture import (
    E2eDeterministicFixtureService,
    E2eDeterministicOutcome,
)
from app.core.config import get_settings
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.session import get_session_factory
from app.main import app
from app.schemas.contracts import BusinessIdeaValidationRunStatus
from app.workers.biv_run_dispatcher import reset_biv_run_dispatcher
from tests.conftest import _create_user_with_api_key
from tests.test_runtime_01a_biv_durable_lifecycle import _seed_biv_request


@pytest.fixture(autouse=True)
def _runtime_dispatcher_reset() -> None:
    reset_biv_run_dispatcher()
    yield
    reset_biv_run_dispatcher()


@pytest.fixture
def biv_runtime_01f_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUSINESS_IDEA_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("MCP_READ_ONLY_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "true")
    monkeypatch.setenv("BIV_RUN_DISPATCHER_ENABLED", "true")
    monkeypatch.setenv("BIV_E2E_DETERMINISTIC_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()


async def _bind_fixture(
    db_session,
    owner_id: UUID,
    outcome: E2eDeterministicOutcome,
    *,
    e2e_run_id: str,
) -> None:
    svc = E2eDeterministicFixtureService(db_session, get_settings())
    await svc.bind_for_owner(owner_id, outcome, e2e_run_id=e2e_run_id)
    await db_session.commit()


async def _enqueue_canonical(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: dict,
    *,
    idempotency_key: str | None = None,
    rerun_intent: bool = False,
) -> UUID:
    body = dict(seeded["run_body"])
    if idempotency_key is not None:
        body["idempotency_key"] = idempotency_key
    if rerun_intent:
        body["rerun_intent"] = True
    resp = await client.post(
        f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 202, resp.text
    return UUID(resp.json()["run_id"])


async def _wait_for_terminal(
    run_id: UUID,
    *,
    expect_status: BusinessIdeaValidationRunStatus,
    timeout_seconds: float = 6.0,
) -> BusinessIdeaValidationRunTable:
    factory = get_session_factory()
    row: BusinessIdeaValidationRunTable | None = None
    last_status: BusinessIdeaValidationRunStatus | None = None
    attempts = max(1, int(timeout_seconds / 0.05))
    for _ in range(attempts):
        async with factory() as session:
            row = await session.get(BusinessIdeaValidationRunTable, run_id)
            assert row is not None
            last_status = row.status
            if row.status in {
                BusinessIdeaValidationRunStatus.SUCCEEDED,
                BusinessIdeaValidationRunStatus.FAILED,
            }:
                break
        await asyncio.sleep(0.05)
    assert row is not None
    if row.status not in {
        BusinessIdeaValidationRunStatus.SUCCEEDED,
        BusinessIdeaValidationRunStatus.FAILED,
    }:
        raise TimeoutError(
            f"biv_run_terminal_timeout: run_id={run_id} last_status={last_status}",
        )
    assert row.status == expect_status
    return row


@pytest.mark.asyncio
async def test_runtime_01f_fixture_bind_forbidden_when_disabled(
    db_session,
    biv_runtime_01f_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIV_E2E_DETERMINISTIC_ENABLED", "false")
    get_settings.cache_clear()
    _api_key, user = await _create_user_with_api_key()
    svc = E2eDeterministicFixtureService(db_session, get_settings())
    with pytest.raises(RuntimeError, match="e2e_deterministic_fixture_forbidden"):
        await svc.bind_for_owner(
            user.id,
            E2eDeterministicOutcome.VERDICT,
            e2e_run_id="disabled-bind",
        )


@pytest.mark.asyncio
async def test_runtime_01f_fixture_resolve_none_in_production(
    db_session,
    biv_runtime_01f_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIV_E2E_DETERMINISTIC_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    _api_key, user = await _create_user_with_api_key()

    # Direct DB insert bypasses bind guard — production runtime must still ignore it.
    from app.db.repositories.biv_e2e_deterministic_fixtures import (
        BivE2eDeterministicFixtureRepository,
    )

    repo = BivE2eDeterministicFixtureRepository(db_session)
    await repo.upsert(
        owner_id=user.id,
        outcome=E2eDeterministicOutcome.VERDICT.value,
        e2e_run_id="prod-ignore",
    )
    await db_session.commit()

    svc = E2eDeterministicFixtureService(db_session, get_settings())
    assert await svc.resolve_for_owner(user.id) is None


@pytest.mark.asyncio
async def test_runtime_01f_deterministic_verdict_persisted(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key, user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        await _bind_fixture(
            db_session,
            user.id,
            E2eDeterministicOutcome.VERDICT,
            e2e_run_id="verdict-scenario",
        )
        run_id = await _enqueue_canonical(client, headers, seeded)
        row = await _wait_for_terminal(run_id, expect_status=BusinessIdeaValidationRunStatus.SUCCEEDED)
        assert row.result_json is not None
        assert row.result_json.get("result_kind") != "partial_research"
        assert row.result_json.get("business_verdict_id") is not None
        assert row.business_verdict_id is None

        get_resp = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}",
            headers=headers,
        )
        assert get_resp.status_code == 200, get_resp.text
        body = get_resp.json()
        assert body["status"] == "succeeded"
        assert body["output"] is not None
        assert body["output"]["customer_report"] is not None
        assert body["output"]["result_kind"] != "partial_research"

        latest = await client.get(
            f"/projects/{seeded['project_id']}/business-idea-validation/latest",
            headers=headers,
        )
        assert latest.status_code == 200, latest.text
        assert latest.json()["run_id"] == str(run_id)


@pytest.mark.asyncio
async def test_runtime_01f_deterministic_partial_persisted(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key, user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        await _bind_fixture(
            db_session,
            user.id,
            E2eDeterministicOutcome.PARTIAL,
            e2e_run_id="partial-scenario",
        )
        run_id = await _enqueue_canonical(client, headers, seeded)
        row = await _wait_for_terminal(run_id, expect_status=BusinessIdeaValidationRunStatus.FAILED)
        assert row.error_code == "high_impact_insufficient_sources"
        assert row.result_json is not None
        assert row.result_json["result_kind"] == "partial_research"
        assert row.result_json["research_terminal_state"] == "succeeded_insufficient"
        assert row.result_json["customer_report"] is None
        assert row.result_json["commercial_verdict"] is None
        assert row.business_verdict_id is None

        get_resp = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}",
            headers=headers,
        )
        assert get_resp.status_code == 200, get_resp.text
        body = get_resp.json()
        assert body["status"] == "failed"
        assert body["output"] is not None
        assert body["output"]["result_kind"] == "partial_research"
        assert body["output"]["research_terminal_state"] == "succeeded_insufficient"
        assert body["output"]["customer_report"] is None
        assert body["output"]["commercial_verdict"] is None


@pytest.mark.asyncio
async def test_runtime_01f_deterministic_technical_failure_no_partial(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key, user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        await _bind_fixture(
            db_session,
            user.id,
            E2eDeterministicOutcome.TECHNICAL,
            e2e_run_id="technical-scenario",
        )
        run_id = await _enqueue_canonical(client, headers, seeded)
        row = await _wait_for_terminal(run_id, expect_status=BusinessIdeaValidationRunStatus.FAILED)
        assert row.error_code == "pipeline_fetch_failed"
        assert row.result_json is None

        get_resp = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}",
            headers=headers,
        )
        assert get_resp.status_code == 200, get_resp.text
        body = get_resp.json()
        assert body["status"] == "failed"
        assert body["output"] is None


@pytest.mark.asyncio
async def test_runtime_01f_parallel_fixture_isolation(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key_a, user_a = await _create_user_with_api_key()
    api_key_b, user_b = await _create_user_with_api_key()
    headers_a = {"Authorization": f"Bearer {api_key_a}"}
    headers_b = {"Authorization": f"Bearer {api_key_b}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded_a = await _seed_biv_request(client, headers_a)
        seeded_b = await _seed_biv_request(client, headers_b)
        await _bind_fixture(
            db_session,
            user_a.id,
            E2eDeterministicOutcome.VERDICT,
            e2e_run_id="parallel-a",
        )
        await _bind_fixture(
            db_session,
            user_b.id,
            E2eDeterministicOutcome.PARTIAL,
            e2e_run_id="parallel-b",
        )

        run_a = await _enqueue_canonical(client, headers_a, seeded_a)
        run_b = await _enqueue_canonical(client, headers_b, seeded_b)

        row_a = await _wait_for_terminal(run_a, expect_status=BusinessIdeaValidationRunStatus.SUCCEEDED)
        row_b = await _wait_for_terminal(run_b, expect_status=BusinessIdeaValidationRunStatus.FAILED)

        assert row_a.result_json is not None
        assert row_a.result_json.get("business_verdict_id") is not None
        assert row_b.error_code == "high_impact_insufficient_sources"
        assert row_b.result_json is not None
        assert row_b.result_json["result_kind"] == "partial_research"


@pytest.mark.asyncio
async def test_runtime_01f_cross_tenant_run_and_latest_hidden(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key_a, user_a = await _create_user_with_api_key()
    api_key_b, _user_b = await _create_user_with_api_key()
    headers_a = {"Authorization": f"Bearer {api_key_a}"}
    headers_b = {"Authorization": f"Bearer {api_key_b}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers_a)
        await _bind_fixture(
            db_session,
            user_a.id,
            E2eDeterministicOutcome.VERDICT,
            e2e_run_id="cross-tenant",
        )
        run_id = await _enqueue_canonical(client, headers_a, seeded)
        await _wait_for_terminal(run_id, expect_status=BusinessIdeaValidationRunStatus.SUCCEEDED)

        foreign_run = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}",
            headers=headers_b,
        )
        assert foreign_run.status_code == 404

        foreign_latest = await client.get(
            f"/projects/{seeded['project_id']}/business-idea-validation/latest",
            headers=headers_b,
        )
        assert foreign_latest.status_code == 404

        foreign_progress = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}/progress",
            headers=headers_b,
        )
        assert foreign_progress.status_code == 404


@pytest.mark.asyncio
async def test_runtime_01f_partial_rerun_creates_new_run(
    db_session,
    biv_runtime_01f_env,
) -> None:
    from app.services.business_idea_validation_service import build_rerun_idempotency_key

    api_key, user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        await _bind_fixture(
            db_session,
            user.id,
            E2eDeterministicOutcome.PARTIAL,
            e2e_run_id="partial-rerun",
        )
        first_id = await _enqueue_canonical(client, headers, seeded)
        await _wait_for_terminal(first_id, expect_status=BusinessIdeaValidationRunStatus.FAILED)

        await _bind_fixture(
            db_session,
            user.id,
            E2eDeterministicOutcome.VERDICT,
            e2e_run_id="partial-rerun-verdict",
        )
        rerun_key = build_rerun_idempotency_key(
            UUID(seeded["context_id"]),
            seeded["snapshot_hash"],
        )
        second_id = await _enqueue_canonical(
            client,
            headers,
            seeded,
            idempotency_key=rerun_key,
            rerun_intent=True,
        )
        assert second_id != first_id
        await _wait_for_terminal(second_id, expect_status=BusinessIdeaValidationRunStatus.SUCCEEDED)

        get_resp = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{second_id}",
            headers=headers,
        )
        assert get_resp.status_code == 200, get_resp.text
        rerun_body = get_resp.json()
        assert rerun_body["status"] == "succeeded"
        assert rerun_body["output"] is not None
        assert rerun_body["output"]["result_kind"] != "partial_research"
        assert rerun_body["output"]["customer_report"] is not None

        latest = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation",
            headers=headers,
        )
        assert latest.status_code == 200, get_resp.text
        assert latest.json()["run_id"] == str(second_id)
        assert latest.json()["status"] == "succeeded"


@pytest.mark.asyncio
async def test_runtime_01f_terminal_restore_does_not_need_fixture(
    db_session,
    biv_runtime_01f_env,
) -> None:
    api_key, user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        await _bind_fixture(
            db_session,
            user.id,
            E2eDeterministicOutcome.VERDICT,
            e2e_run_id="restore-scenario",
        )
        run_id = await _enqueue_canonical(client, headers, seeded)
        await _wait_for_terminal(run_id, expect_status=BusinessIdeaValidationRunStatus.SUCCEEDED)

        svc = E2eDeterministicFixtureService(db_session, get_settings())
        assert await svc.resolve_for_owner(user.id) is None

        get_resp = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}",
            headers=headers,
        )
        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["status"] == "succeeded"
