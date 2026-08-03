"""RUNTIME-01A — durable in-process BIV run lifecycle tests."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.business_idea_validation.skill import BusinessIdeaValidationSkill
from app.core.config import get_settings
from app.core.exceptions import ResearchPipelineError
from app.db.base import utc_now
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.repositories.business_idea_validation_runs import BusinessIdeaValidationRunRepository
from app.db.session import get_session_factory
from app.main import app
from app.schemas.contracts import (
    AnalysisContextConfirmRequest,
    AnalysisContextCreateDraftRequest,
    BusinessIdeaValidationRunStatus,
    BusinessIdeaValidationVerdictKind,
)
from app.services.business_idea_validation_service import build_research_idempotency_key
from app.workers.biv_run_dispatcher import get_biv_run_dispatcher, reset_biv_run_dispatcher
from tests.conftest import _create_user_with_api_key
from tests.test_cwf_1a_launch_pack_decision import _output

IDEA = (
    "AI-платформа для автоматического создания коммерческих "
    "предложений для строительных компаний"
)


async def _seed_biv_request(client: AsyncClient, headers: dict[str, str]) -> dict:
    project = await client.post("/projects", json={"name": "RUNTIME-01A"}, headers=headers)
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    draft = await client.post(
        f"/projects/{project_id}/analysis-contexts",
        json=AnalysisContextCreateDraftRequest(
            idea_description=IDEA,
            product_or_service="SaaS генерации КП для строительного B2B",
            target_customer="Коммерческие директора строительных компаний 50–500 сотрудников",
            geography="Россия, B2B",
            analysis_goal="Проверить спрос и конкуренцию перед запуском",
        ).model_dump(mode="json"),
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    context = draft.json()
    context_id = context["context_id"]
    snapshot_hash = context["input_snapshot_hash"]

    confirmed = await client.post(
        f"/projects/{project_id}/analysis-contexts/{context_id}/confirm",
        json=AnalysisContextConfirmRequest(input_snapshot_hash=snapshot_hash).model_dump(mode="json"),
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text

    user_request = await client.post(
        "/user-requests",
        json={
            "text": IDEA,
            "selected_scenario": "idea_validation",
            "skill_inputs": {"home_agency_flow": "v2"},
        },
        headers=headers,
    )
    assert user_request.status_code == 201, user_request.text
    request_id = user_request.json()["id"]
    idem_key = build_research_idempotency_key(context_id, snapshot_hash)

    return {
        "project_id": project_id,
        "context_id": context_id,
        "snapshot_hash": snapshot_hash,
        "request_id": request_id,
        "idem_key": idem_key,
        "run_body": {
            "idempotency_key": idem_key,
            "research_intent": True,
            "analysis_context_id": context_id,
            "input_snapshot_hash": snapshot_hash,
            "idea": IDEA,
            "location": "Россия, B2B",
            "target_audience": "Коммерческие директора строительных компаний",
        },
    }


@pytest.fixture(autouse=True)
def _runtime_dispatcher_reset() -> None:
    reset_biv_run_dispatcher()
    yield
    reset_biv_run_dispatcher()


@pytest.fixture
def biv_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUSINESS_IDEA_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("MCP_READ_ONLY_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "true")
    monkeypatch.setenv("BIV_RUN_DISPATCHER_ENABLED", "true")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_runtime_01a_post_returns_202_before_pipeline_terminal(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = asyncio.Event()

    async def slow_run(self, inp, **kwargs):
        await gate.wait()
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", slow_run)

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
        body = resp.json()
        assert body["status"] in {
            BusinessIdeaValidationRunStatus.QUEUED.value,
            BusinessIdeaValidationRunStatus.RUNNING.value,
        }
        run_id = UUID(body["run_id"])

        factory = get_session_factory()
        async with factory() as session:
            row = await session.get(BusinessIdeaValidationRunTable, run_id)
            assert row is not None
            assert row.status in {
                BusinessIdeaValidationRunStatus.QUEUED,
                BusinessIdeaValidationRunStatus.RUNNING,
            }

        gate.set()
        for _ in range(100):
            async with factory() as session:
                row = await session.get(BusinessIdeaValidationRunTable, run_id)
                assert row is not None
                if row.status == BusinessIdeaValidationRunStatus.SUCCEEDED:
                    break
            await asyncio.sleep(0.05)
        assert row.status == BusinessIdeaValidationRunStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_runtime_01a_duplicate_active_returns_same_run_id(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = asyncio.Event()

    async def slow_run(self, inp, **kwargs):
        await gate.wait()
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", slow_run)

    api_key, _user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        first = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
            json=seeded["run_body"],
            headers=headers,
        )
        assert first.status_code == 202
        second = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
            json=seeded["run_body"],
            headers=headers,
        )
        assert second.status_code == 202
        assert second.json()["run_id"] == first.json()["run_id"]
        assert second.json()["lineage_reused"] is True
        gate.set()


@pytest.mark.asyncio
async def test_runtime_01a_pipeline_error_marks_failed(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_run(self, inp, **kwargs):
        raise ResearchPipelineError(
            failure_code="high_impact_insufficient_sources",
            safe_message="Not enough sources",
            failure_stage="generating_verdict",
        )

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", failing_run)

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

        factory = get_session_factory()
        for _ in range(100):
            async with factory() as session:
                row = await session.get(BusinessIdeaValidationRunTable, run_id)
                assert row is not None
                if row.status == BusinessIdeaValidationRunStatus.FAILED:
                    break
            await asyncio.sleep(0.05)

        assert row.status == BusinessIdeaValidationRunStatus.FAILED
        assert row.error_code == "high_impact_insufficient_sources"


@pytest.mark.asyncio
async def test_runtime_01a_unhandled_exception_not_eternal_running(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom_run(self, inp, **kwargs):
        raise RuntimeError("provider_secret_leak_should_not_persist")

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", boom_run)

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
        run_id = UUID(resp.json()["run_id"])
        factory = get_session_factory()
        for _ in range(100):
            async with factory() as session:
                row = await session.get(BusinessIdeaValidationRunTable, run_id)
                assert row is not None
                if row.status == BusinessIdeaValidationRunStatus.FAILED:
                    break
            await asyncio.sleep(0.05)
        assert row.status == BusinessIdeaValidationRunStatus.FAILED


@pytest.mark.asyncio
async def test_runtime_01a_progress_readable_from_fresh_session(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        run_id = UUID(resp.json()["run_id"])
        for _ in range(100):
            progress_resp = await client.get(
                f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}/progress",
                headers=headers,
            )
            assert progress_resp.status_code == 200
            if progress_resp.json()["state"] == BusinessIdeaValidationRunStatus.SUCCEEDED.value:
                break
            await asyncio.sleep(0.05)
        assert progress_resp.json()["state"] == BusinessIdeaValidationRunStatus.SUCCEEDED.value


@pytest.mark.asyncio
async def test_runtime_01a_startup_redispatches_queued(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = asyncio.Event()

    async def slow_run(self, inp, **kwargs):
        await gate.wait()
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", slow_run)

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

    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(BusinessIdeaValidationRunTable, run_id)
        assert row is not None
        row.status = BusinessIdeaValidationRunStatus.QUEUED
        session.add(row)
        await session.commit()

    async def fast_run(self, inp, **kwargs):
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", fast_run)
    reset_biv_run_dispatcher()
    recovery = await get_biv_run_dispatcher().recover_on_startup()
    assert recovery["queued_redispatched"] >= 1

    gate.set()
    for _ in range(100):
        async with factory() as session:
            row = await session.get(BusinessIdeaValidationRunTable, run_id)
            assert row is not None
            if row.status == BusinessIdeaValidationRunStatus.SUCCEEDED:
                break
        await asyncio.sleep(0.05)
    assert row.status == BusinessIdeaValidationRunStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_runtime_01a_stale_running_becomes_interrupted(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def noop_dispatch(self, run_id: UUID) -> None:
        return None

    monkeypatch.setattr(
        "app.workers.biv_run_dispatcher.BivRunDispatcher.dispatch",
        noop_dispatch,
    )

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
        run_id = UUID(resp.json()["run_id"])

    stale_time = utc_now() - timedelta(seconds=3600)
    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(BusinessIdeaValidationRunTable, run_id)
        assert row is not None
        row.status = BusinessIdeaValidationRunStatus.RUNNING
        row.updated_at = stale_time
        session.add(row)
        await session.commit()

    reset_biv_run_dispatcher()
    recovery = await get_biv_run_dispatcher().recover_on_startup()
    assert recovery["stale_interrupted"] >= 1

    async with factory() as session:
        row = await session.get(BusinessIdeaValidationRunTable, run_id)
        assert row is not None
        assert row.status == BusinessIdeaValidationRunStatus.FAILED
        assert row.error_code == "research_execution_interrupted"


@pytest.mark.asyncio
async def test_runtime_01a_concurrent_requests_single_active_run(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = asyncio.Event()

    async def slow_run(self, inp, **kwargs):
        await gate.wait()
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", slow_run)

    api_key, user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        url = f"/user-requests/{seeded['request_id']}/business-idea-validation/runs"
        first = await client.post(url, json=seeded["run_body"], headers=headers)
        assert first.status_code == 202
        responses = await asyncio.gather(
            client.post(url, json=seeded["run_body"], headers=headers),
            client.post(url, json=seeded["run_body"], headers=headers),
        )
        assert all(r.status_code == 202 for r in responses)
        run_ids = {UUID(r.json()["run_id"]) for r in [first, *responses]}
        assert len(run_ids) == 1

        factory = get_session_factory()
        async with factory() as session:
            repo = BusinessIdeaValidationRunRepository(session)
            row = await repo.get_by_idempotency_key(user.id, seeded["idem_key"])
            assert row is not None
            assert row.id in run_ids
        gate.set()


@pytest.mark.asyncio
async def test_runtime_01a_terminal_run_not_restarted(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    async def counting_run(self, inp, **kwargs):
        calls["count"] += 1
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", counting_run)

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
        run_id = UUID(resp.json()["run_id"])
        factory = get_session_factory()
        for _ in range(100):
            async with factory() as session:
                row = await session.get(BusinessIdeaValidationRunTable, run_id)
                assert row is not None
                if row.status == BusinessIdeaValidationRunStatus.SUCCEEDED:
                    break
            await asyncio.sleep(0.05)

        before = calls["count"]
        await get_biv_run_dispatcher().dispatch(run_id)
        await asyncio.sleep(0.2)
        assert calls["count"] == before
