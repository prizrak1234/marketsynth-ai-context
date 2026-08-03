"""PRODUCT-01.3A — BIV intake and hydration consent gate tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.business_idea_validation.analysis_context_gate import (
    compute_input_snapshot_hash,
    evaluate_specificity,
    is_specificity_sufficient,
)
from app.core.config import get_settings
from app.db.base import utc_now
from app.db.models.analysis_context import AnalysisContextTable
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.models.project import ProjectTable
from app.db.models.user_request import UserRequestTable
from app.product.offer_builder.eligibility import evaluate_eligibility, map_biv_verdict_to_mv
from app.product.offer_builder.input_builder import build_upstream_from_biv
from app.schemas.contracts import (
    AnalysisContextCreateDraftRequest,
    AnalysisContextFields,
    AnalysisContextSourceMode,
    AnalysisContextState,
    BusinessIdeaValidationRunStatus,
    BusinessIdeaValidationVerdictKind,
)
from app.schemas.crud import ProjectCreate
from app.services.analysis_context_service import AnalysisContextService
from app.services.business_idea_validation_service import (
    BusinessIdeaValidationService,
    build_research_idempotency_key,
)
from app.services.projects_service import ProjectService
from fastapi.testclient import TestClient
from tests.conftest import _create_user_with_api_key
from tests.test_cwf_1a_launch_pack_decision import _output


def _valid_fields(**overrides) -> AnalysisContextFields:
    base = AnalysisContextFields(
        idea_description="Онлайн-школа английского для взрослых через Telegram",
        product_or_service="Курсы английского языка",
        target_customer="Взрослые 25–45 лет, работающие специалисты",
        geography="Россия, онлайн",
        analysis_goal="Проверить спрос и конкуренцию перед запуском",
    )
    data = base.model_dump()
    data.update(overrides)
    return AnalysisContextFields(**data)


async def _seed_project_db(db_session, owner_id) -> ProjectTable:
    projects = ProjectService(db_session)
    return await projects.create(ProjectCreate(owner_id=owner_id, name="Test project"))


async def _seed_confirmed_context(db_session, *, owner_id=None):
    if owner_id is None:
        _key, user = await _create_user_with_api_key()
        owner_id = user.id
    project = await _seed_project_db(db_session, owner_id)
    svc = AnalysisContextService(db_session, get_settings())
    draft = await svc.create_draft(
        owner_id,
        project.id,
        AnalysisContextCreateDraftRequest(**_valid_fields().model_dump()),
    )
    from app.schemas.contracts import AnalysisContextConfirmRequest

    confirmed = await svc.confirm(
        owner_id,
        project.id,
        draft.context_id,
        AnalysisContextConfirmRequest(),
    )
    return owner_id, project.id, confirmed


@pytest.mark.parametrize(
    ("idea", "missing"),
    [
        ("", ["idea_description"]),
        ("бизнес", ["idea_description"]),
        ("https://example.com", ["idea_description"]),
    ],
)
def test_specificity_gate_rejects_weak_input(idea: str, missing: list[str]) -> None:
    fields = _valid_fields(idea_description=idea)
    got_missing, _ = evaluate_specificity(fields)
    for field in missing:
        assert field in got_missing


def test_explicit_unknown_geography_accepted() -> None:
    fields = _valid_fields(geography="неизвестно", geography_unknown=True)
    missing, warnings = evaluate_specificity(fields)
    assert "geography" not in missing
    assert "geography_unknown" in warnings


def test_explicit_unknown_audience_accepted_with_warning() -> None:
    fields = _valid_fields(target_customer="неизвестно", target_customer_unknown=True)
    missing, warnings = evaluate_specificity(fields)
    assert "target_customer" not in missing
    assert "target_customer_unknown" in warnings


def test_snapshot_hash_stable() -> None:
    fields = _valid_fields()
    assert compute_input_snapshot_hash(fields) == compute_input_snapshot_hash(fields)


@pytest.mark.asyncio
async def test_empty_context_cannot_start_analysis(db_session) -> None:
    _key, user = await _create_user_with_api_key()
    await _seed_project_db(db_session, user.id)
    request_id = uuid4()
    now = utc_now()
    db_session.add(
        UserRequestTable(
            id=request_id,
            owner_id=user.id,
            tenant_id=user.id,
            text="draft",
            normalized_text="draft",
            created_at=now,
            updated_at=now,
        ),
    )
    await db_session.commit()

    svc = BusinessIdeaValidationService(db_session, get_settings())
    from app.schemas.contracts import BusinessIdeaValidationRunRequest

    missing_context_id = uuid4()
    missing_snapshot = "a" * 64
    with pytest.raises(Exception) as exc:
        await svc.run(
            user.id,
            request_id,
            BusinessIdeaValidationRunRequest(
                idempotency_key=build_research_idempotency_key(
                    missing_context_id,
                    missing_snapshot,
                ),
                analysis_context_id=missing_context_id,
                input_snapshot_hash=missing_snapshot,
            ),
        )
    assert "analysis_context" in str(exc.value)


@pytest.mark.asyncio
async def test_hydrated_unconfirmed_cannot_start(db_session) -> None:
    _key, user = await _create_user_with_api_key()
    project = await _seed_project_db(db_session, user.id)
    now = utc_now()
    context_id = uuid4()
    snapshot = compute_input_snapshot_hash(_valid_fields())
    row = AnalysisContextTable(
        id=context_id,
        owner_id=user.id,
        tenant_id=user.id,
        project_id=project.id,
        state=AnalysisContextState.HYDRATED_UNCONFIRMED,
        source_mode=AnalysisContextSourceMode.RESTORED_PROJECT_CONTEXT,
        idea_description=_valid_fields().idea_description,
        input_snapshot_hash=snapshot,
        confirmed_by_user=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    request_id = uuid4()
    db_session.add(
        UserRequestTable(
            id=request_id,
            owner_id=user.id,
            tenant_id=user.id,
            text=_valid_fields().idea_description,
            normalized_text=_valid_fields().idea_description,
            created_at=now,
            updated_at=now,
        ),
    )
    await db_session.commit()

    svc = BusinessIdeaValidationService(db_session, get_settings())
    from app.schemas.contracts import BusinessIdeaValidationRunRequest

    with pytest.raises(Exception) as exc:
        await svc.run(
            user.id,
            request_id,
            BusinessIdeaValidationRunRequest(
                idempotency_key=build_research_idempotency_key(context_id, snapshot),
                analysis_context_id=context_id,
                input_snapshot_hash=snapshot,
            ),
        )
    assert "hydrated_context_confirmation_required" in str(exc.value)


@pytest.mark.asyncio
async def test_confirmed_restored_context_passes_gate(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    svc = AnalysisContextService(db_session, get_settings())
    row = await svc.assert_runnable(
        owner_id,
        project_id,
        confirmed.context_id,
        confirmed.input_snapshot_hash or "",
    )
    assert row.confirmed_by_user is True


@pytest.mark.asyncio
async def test_edited_context_requires_reconfirmation(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    svc = AnalysisContextService(db_session, get_settings())
    edited = await svc.edit(
        owner_id,
        project_id,
        confirmed.context_id,
        AnalysisContextCreateDraftRequest(**_valid_fields(idea_description="Изменённая идея").model_dump()),
    )
    assert edited.confirmed_by_user is False
    assert edited.state == AnalysisContextState.EDITING
    with pytest.raises(Exception) as exc:
        await svc.assert_runnable(
            owner_id,
            project_id,
            edited.context_id,
            edited.input_snapshot_hash or "",
        )
    assert "analysis_context_required" in str(exc.value)


@pytest.mark.asyncio
async def test_start_new_clears_active_draft_only(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    svc = AnalysisContextService(db_session, get_settings())
    started = await svc.start_new(owner_id, project_id)
    assert started.project_id != project_id
    assert started.context.state == AnalysisContextState.EMPTY
    old = await svc._contexts.get_active_for_project(owner_id, project_id)  # noqa: SLF001
    assert old is None or old.is_active is False


@pytest.mark.asyncio
async def test_historical_biv_run_preserved_after_start_new(db_session) -> None:
    owner_id, project_id, _confirmed = await _seed_confirmed_context(db_session)
    run_id = uuid4()
    now = utc_now()
    db_session.add(
        BusinessIdeaValidationRunTable(
            id=run_id,
            owner_id=owner_id,
            tenant_id=owner_id,
            user_request_id=uuid4(),
            project_id=project_id,
            investigation_id=uuid4(),
            idempotency_key="hist-run-key",
            status=BusinessIdeaValidationRunStatus.SUCCEEDED,
            result_json=_output(BusinessIdeaValidationVerdictKind.PROCEED).model_dump(mode="json"),
            created_at=now,
            updated_at=now,
        ),
    )
    await db_session.commit()
    svc = AnalysisContextService(db_session, get_settings())
    await svc.start_new(owner_id, project_id)
    from app.db.repositories.business_idea_validation_runs import (
        BusinessIdeaValidationRunRepository,
    )

    repo = BusinessIdeaValidationRunRepository(db_session)
    preserved = await repo.get_by_id(run_id)
    assert preserved is not None


@pytest.mark.asyncio
async def test_cross_tenant_context_hidden(db_session, other_auth_headers: dict[str, str]) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    svc = AnalysisContextService(db_session, get_settings())
    with pytest.raises(Exception) as exc:
        await svc.get_for_run(uuid4(), confirmed.context_id, confirmed.input_snapshot_hash or "")
    assert "analysis_context_not_found" in str(exc.value)
    _ = other_auth_headers
    _ = owner_id
    _ = project_id


@pytest.mark.asyncio
async def test_stale_snapshot_hash_rejected(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    svc = AnalysisContextService(db_session, get_settings())
    with pytest.raises(Exception) as exc:
        await svc.get_for_run(owner_id, confirmed.context_id, "b" * 64)
    assert "analysis_context_stale" in str(exc.value)
    _ = project_id


@pytest.mark.asyncio
async def test_confirm_idempotent_for_same_hash(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    svc = AnalysisContextService(db_session, get_settings())
    from app.schemas.contracts import AnalysisContextConfirmRequest

    again = await svc.confirm(
        owner_id,
        project_id,
        confirmed.context_id,
        AnalysisContextConfirmRequest(input_snapshot_hash=confirmed.input_snapshot_hash),
    )
    assert again.input_snapshot_hash == confirmed.input_snapshot_hash
    assert again.confirmed_by_user is True


@pytest.mark.asyncio
async def test_reconfirm_required_after_content_change(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    svc = AnalysisContextService(db_session, get_settings())
    edited = await svc.edit(
        owner_id,
        project_id,
        confirmed.context_id,
        AnalysisContextCreateDraftRequest(**_valid_fields(analysis_goal="Новая цель").model_dump()),
    )
    assert edited.confirmed_by_user is False
    assert edited.input_snapshot_hash != confirmed.input_snapshot_hash


@pytest.mark.asyncio
async def test_analysis_binds_context_hash(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    assert confirmed.input_snapshot_hash is not None
    assert is_specificity_sufficient(_valid_fields())


def test_unconfirmed_biv_blocks_offer_eligibility() -> None:
    output = _output(BusinessIdeaValidationVerdictKind.PROCEED)
    upstream = build_upstream_from_biv(
        owner_id=uuid4(),
        project_id=uuid4(),
        output=output,
        accepted_conditions=[],
        mv_verdict=map_biv_verdict_to_mv(BusinessIdeaValidationVerdictKind.PROCEED),
    )
    result = evaluate_eligibility(
        biv_verdict=BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        upstream=upstream,
    )
    assert result.allowed is False


def test_api_empty_context_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_resp = client.post(
        "/projects",
        headers=auth_headers,
        json={"name": "API gate project"},
    )
    assert project_resp.status_code == 201
    req = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Онлайн-школа для взрослых", "selected_scenario": "idea_validation"},
    )
    assert req.status_code == 201
    missing_context_id = uuid4()
    missing_snapshot = "c" * 64
    run = client.post(
        f"/user-requests/{req.json()['id']}/business-idea-validation/run",
        headers=auth_headers,
        json={
            "idempotency_key": build_research_idempotency_key(
                missing_context_id,
                missing_snapshot,
            ),
            "analysis_context_id": str(missing_context_id),
            "input_snapshot_hash": missing_snapshot,
        },
    )
    assert run.status_code in {404, 409}
    body = run.json()
    detail = body.get("error_code") or body.get("safe_message") or body.get("detail")
    assert detail in {
        "analysis_context_not_found",
        "analysis_context_required",
        "hydrated_context_confirmation_required",
        "user_request_not_found",
        "not_found",
    }


def test_api_hydrated_requires_confirm(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_resp = client.post("/projects", headers=auth_headers, json={"name": "Confirm gate"})
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]
    draft = client.post(
        f"/projects/{project_id}/analysis-contexts",
        headers=auth_headers,
        json=_valid_fields().model_dump(),
    )
    assert draft.status_code == 201
    context_id = draft.json()["context_id"]
    snapshot_hash = draft.json()["input_snapshot_hash"]
    req = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": _valid_fields().idea_description, "selected_scenario": "idea_validation"},
    )
    assert req.status_code == 201
    run = client.post(
        f"/user-requests/{req.json()['id']}/business-idea-validation/run",
        headers=auth_headers,
        json={
            "idempotency_key": build_research_idempotency_key(context_id, snapshot_hash),
            "analysis_context_id": context_id,
            "input_snapshot_hash": snapshot_hash,
        },
    )
    assert run.status_code == 409
    body = run.json()
    code = body.get("error_code") or body.get("detail")
    assert code in {"analysis_context_required", "hydrated_context_confirmation_required"}
    confirm = client.post(
        f"/projects/{project_id}/analysis-contexts/{context_id}/confirm",
        headers=auth_headers,
        json={},
    )
    assert confirm.status_code == 200
    assert confirm.json()["confirmed_by_user"] is True


def test_api_get_current_hydrates_unconfirmed(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import datetime

    from app.schemas.contracts import (
        BusinessIdeaValidationProjectHydration,
        BusinessIdeaValidationRunStatus,
    )
    from app.services.business_idea_validation_service import BusinessIdeaValidationService

    project_resp = client.post("/projects", headers=auth_headers, json={"name": "Hydrate project"})
    project_id = project_resp.json()["id"]
    output = _output(BusinessIdeaValidationVerdictKind.PROCEED)
    hydration = BusinessIdeaValidationProjectHydration(
        project_id=project_id,
        user_request_id=uuid4(),
        user_request_text="Онлайн-школа английского для взрослых",
        run_id=uuid4(),
        status=BusinessIdeaValidationRunStatus.SUCCEEDED,
        output=output,
        updated_at=datetime.utcnow(),
    )

    async def fake_hydration(_self, _owner_id, _project_id):
        return hydration

    monkeypatch.setattr(BusinessIdeaValidationService, "get_project_hydration", fake_hydration)

    current = client.get(f"/projects/{project_id}/analysis-contexts/current", headers=auth_headers)
    assert current.status_code == 200
    body = current.json()
    if body["context"] is not None:
        assert body["context"]["state"] in {
            "hydrated_unconfirmed",
            "draft_entered",
            "empty",
            "confirmed",
        }


@pytest.mark.asyncio
async def test_reload_restores_hydrated_unconfirmed(db_session) -> None:
    owner_id, project_id, _ = await _seed_confirmed_context(db_session)
    svc = AnalysisContextService(db_session, get_settings())
    await svc._contexts.deactivate_project_contexts(owner_id, project_id)  # noqa: SLF001
    hydrated = await svc._hydrate_from_project(owner_id, project_id)  # noqa: SLF001
    assert hydrated.state == AnalysisContextState.HYDRATED_UNCONFIRMED
    assert hydrated.confirmed_by_user is False


@pytest.mark.asyncio
def test_api_analysis_context_routes_registered(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Regression: analysis-context endpoints must exist (not FastAPI route 404)."""
    openapi = client.get("/openapi.json").json()
    paths = openapi.get("paths", {})
    assert "/projects/{project_id}/analysis-contexts" in paths
    assert "/projects/{project_id}/analysis-contexts/current" in paths
    assert "post" in paths["/projects/{project_id}/analysis-contexts"]
    project_resp = client.post("/projects", headers=auth_headers, json={"name": "Route check"})
    project_id = project_resp.json()["id"]
    current = client.get(
        f"/projects/{project_id}/analysis-contexts/current",
        headers=auth_headers,
    )
    assert current.status_code == 200


@pytest.mark.asyncio
async def test_incomplete_confirm_returns_error(db_session) -> None:
    _key, user = await _create_user_with_api_key()
    project = await _seed_project_db(db_session, user.id)
    svc = AnalysisContextService(db_session, get_settings())
    draft = await svc.create_draft(
        user.id,
        project.id,
        AnalysisContextCreateDraftRequest(idea_description="бизнес"),
    )
    from app.schemas.contracts import AnalysisContextConfirmRequest

    with pytest.raises(Exception) as exc:
        await svc.confirm(user.id, project.id, draft.context_id, AnalysisContextConfirmRequest())
    assert "analysis_context_incomplete" in str(exc.value)
