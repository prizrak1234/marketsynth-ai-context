"""RUNTIME-01G — single active BIV run + project latest-run recovery."""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from app.business_idea_validation.skill import BusinessIdeaValidationSkill
from app.core.exceptions import InvalidStateError, ResearchPipelineError
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.models.investigation import InvestigationTable
from app.db.session import get_session_factory
from app.main import app
from app.schemas.contracts import (
    AnalysisContextConfirmRequest,
    AnalysisContextCreateDraftRequest,
    BusinessIdeaValidationRunStatus,
    BusinessIdeaValidationVerdictKind,
    InvestigationStatus,
)
from app.services.business_idea_validation_service import build_research_idempotency_key
from app.workers.biv_run_dispatcher import reset_biv_run_dispatcher
from httpx import ASGITransport, AsyncClient
from tests.conftest import _create_user_with_api_key
from tests.test_cwf_1a_launch_pack_decision import _output
from tests.test_runtime_01a_biv_durable_lifecycle import (
    IDEA,
    _seed_biv_request,
)

pytestmark = pytest.mark.usefixtures("biv_runtime_env")


@pytest.fixture(autouse=True)
def _runtime_dispatcher_reset() -> None:
    reset_biv_run_dispatcher()
    yield
    reset_biv_run_dispatcher()


async def _second_request_same_project(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: str,
) -> dict:
    draft = await client.post(
        f"/projects/{project_id}/analysis-contexts",
        json=AnalysisContextCreateDraftRequest(
            idea_description=IDEA + " — повторная проверка",
            product_or_service="SaaS генерации КП для строительного B2B",
            target_customer="Коммерческие директора строительных компаний 50–500 сотрудников",
            geography="Россия, B2B",
            analysis_goal="Повторная проверка спроса",
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
            "text": IDEA + " — повтор",
            "selected_scenario": "idea_validation",
            "skill_inputs": {"home_agency_flow": "v2"},
        },
        headers=headers,
    )
    assert user_request.status_code == 201, user_request.text
    request_id = user_request.json()["id"]
    idem_key = build_research_idempotency_key(context_id, snapshot_hash)
    return {
        "request_id": request_id,
        "context_id": context_id,
        "snapshot_hash": snapshot_hash,
        "idem_key": idem_key,
        "run_body": {
            "idempotency_key": idem_key,
            "research_intent": True,
            "analysis_context_id": context_id,
            "input_snapshot_hash": snapshot_hash,
            "idea": IDEA,
        },
    }


@pytest.mark.asyncio
async def test_enqueue_reuses_active_run_same_project(db_session) -> None:
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
            first = await client.post(
                f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
                json=seeded["run_body"],
                headers=headers,
            )
            assert first.status_code == 202
            first_id = first.json()["run_id"]

            second_seed = await _second_request_same_project(
                client, headers, seeded["project_id"]
            )
            second = await client.post(
                f"/user-requests/{second_seed['request_id']}/business-idea-validation/runs",
                json=second_seed["run_body"],
                headers=headers,
            )
            assert second.status_code == 202
            assert second.json()["run_id"] == first_id
            assert second.json()["lineage_reused"] is True

            factory = get_session_factory()
            async with factory() as session:
                rows = (
                    await session.execute(
                        BusinessIdeaValidationRunTable.__table__.select().where(
                            BusinessIdeaValidationRunTable.project_id == UUID(seeded["project_id"]),
                            BusinessIdeaValidationRunTable.status.in_(
                                [
                                    BusinessIdeaValidationRunStatus.QUEUED,
                                    BusinessIdeaValidationRunStatus.RUNNING,
                                ]
                            ),
                        )
                    )
                ).all()
                assert len(rows) == 1
    finally:
        skill_mod.BusinessIdeaValidationSkill.run = original
        gate.set()


@pytest.mark.asyncio
async def test_two_concurrent_enqueue_requests_create_one_active_run(db_session) -> None:
    gate = asyncio.Event()
    entered = asyncio.Event()

    async def slow_run(self, inp, **kwargs):
        entered.set()
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
            second_seed = await _second_request_same_project(
                client, headers, seeded["project_id"]
            )

            async def post_first():
                return await client.post(
                    f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
                    json=seeded["run_body"],
                    headers=headers,
                )

            async def post_second():
                await entered.wait()
                return await client.post(
                    f"/user-requests/{second_seed['request_id']}/business-idea-validation/runs",
                    json=second_seed["run_body"],
                    headers=headers,
                )

            first_resp, second_resp = await asyncio.gather(post_first(), post_second())
            assert first_resp.status_code == 202
            assert second_resp.status_code == 202
            assert first_resp.json()["run_id"] == second_resp.json()["run_id"]
    finally:
        skill_mod.BusinessIdeaValidationSkill.run = original
        gate.set()


@pytest.mark.asyncio
async def test_incident_regression_no_supersede_during_active_run(db_session) -> None:
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
            first = await client.post(
                f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
                json=seeded["run_body"],
                headers=headers,
            )
            assert first.status_code == 202
            run_a = UUID(first.json()["run_id"])

            factory = get_session_factory()
            async with factory() as session:
                row_a = await session.get(BusinessIdeaValidationRunTable, run_a)
                assert row_a is not None
                inv_id = row_a.investigation_id

            second_seed = await _second_request_same_project(
                client, headers, seeded["project_id"]
            )
            blocked = await client.post(
                f"/user-requests/{second_seed['request_id']}/business-idea-validation/runs",
                json=second_seed["run_body"],
                headers=headers,
            )
            assert blocked.status_code == 202
            assert blocked.json()["run_id"] == str(run_a)

            async with factory() as session:
                inv = await session.get(InvestigationTable, inv_id)
                assert inv is not None
                assert inv.status != InvestigationStatus.SUPERSEDED

            gate.set()
            for _ in range(120):
                async with factory() as session:
                    row_a = await session.get(BusinessIdeaValidationRunTable, run_a)
                    assert row_a is not None
                    if row_a.status != BusinessIdeaValidationRunStatus.RUNNING:
                        break
                await asyncio.sleep(0.05)
            assert row_a.status == BusinessIdeaValidationRunStatus.SUCCEEDED
            assert row_a.error_code != "investigation_immutable"
    finally:
        skill_mod.BusinessIdeaValidationSkill.run = original
        gate.set()


@pytest.mark.asyncio
async def test_latest_run_returns_technical_failure_without_output(db_session) -> None:
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
            assert resp.status_code == 202
            run_id = UUID(resp.json()["run_id"])
            for _ in range(120):
                get_run = await client.get(
                    f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}",
                    headers=headers,
                )
                if get_run.json()["status"] == "failed":
                    break
                await asyncio.sleep(0.05)

            latest = await client.get(
                f"/projects/{seeded['project_id']}/business-idea-validation/latest-run",
                headers=headers,
            )
            assert latest.status_code == 200
            body = latest.json()
            assert body["status"] == "failed"
            assert body["has_output"] is False
            assert body["safe_error_code"] == "investigation_immutable"
            assert body["progress"]["state"] == "failed"
    finally:
        skill_mod.BusinessIdeaValidationSkill.run = original


@pytest.mark.asyncio
async def test_partial_terminal_progress_consistent(db_session) -> None:
    async def partial_run(self, inp, **kwargs):
        raise ResearchPipelineError(
            failure_code="high_impact_insufficient_sources",
            safe_message="Недостаточно источников",
            failure_stage="generating_verdict",
        )

    import app.business_idea_validation.skill as skill_mod

    original = skill_mod.BusinessIdeaValidationSkill.run
    skill_mod.BusinessIdeaValidationSkill.run = partial_run

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
            for _ in range(120):
                factory = get_session_factory()
                async with factory() as session:
                    row = await session.get(BusinessIdeaValidationRunTable, run_id)
                    assert row is not None
                    if row.status == BusinessIdeaValidationRunStatus.FAILED:
                        assert row.progress_json is not None
                        assert row.progress_json["state"] == "failed"
                        break
                await asyncio.sleep(0.05)
    finally:
        skill_mod.BusinessIdeaValidationSkill.run = original


@pytest.mark.asyncio
async def test_new_run_allowed_after_prior_terminal(
    db_session,
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
        first = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
            json=seeded["run_body"],
            headers=headers,
        )
        run_id = UUID(first.json()["run_id"])
        terminal = False
        for _ in range(120):
            factory = get_session_factory()
            async with factory() as session:
                row = await session.get(BusinessIdeaValidationRunTable, run_id)
                assert row is not None
                if row.status == BusinessIdeaValidationRunStatus.SUCCEEDED:
                    terminal = True
                    break
            await asyncio.sleep(0.05)
        assert terminal, "first run must reach terminal succeeded before second enqueue"

        second_seed = await _second_request_same_project(client, headers, seeded["project_id"])
        second = await client.post(
            f"/user-requests/{second_seed['request_id']}/business-idea-validation/runs",
            json=second_seed["run_body"],
            headers=headers,
        )
        assert second.status_code == 202
        assert second.json()["run_id"] != str(run_id)


@pytest.mark.asyncio
async def test_cross_tenant_active_run_not_disclosed(db_session) -> None:
    gate = asyncio.Event()

    async def slow_run(self, inp, **kwargs):
        await gate.wait()
        return _output(BusinessIdeaValidationVerdictKind.PROCEED, run_id=kwargs.get("run_id"))

    import app.business_idea_validation.skill as skill_mod

    original = skill_mod.BusinessIdeaValidationSkill.run
    skill_mod.BusinessIdeaValidationSkill.run = slow_run

    api_key_a, _user_a = await _create_user_with_api_key(telegram_id=900001)
    api_key_b, _user_b = await _create_user_with_api_key(telegram_id=900002)
    headers_a = {"Authorization": f"Bearer {api_key_a}"}
    headers_b = {"Authorization": f"Bearer {api_key_b}"}
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            seeded_a = await _seed_biv_request(client, headers_a)
            await client.post(
                f"/user-requests/{seeded_a['request_id']}/business-idea-validation/runs",
                json=seeded_a["run_body"],
                headers=headers_a,
            )

            latest_b = await client.get(
                f"/projects/{seeded_a['project_id']}/business-idea-validation/latest-run",
                headers=headers_b,
            )
            assert latest_b.status_code == 404
    finally:
        skill_mod.BusinessIdeaValidationSkill.run = original
        gate.set()
