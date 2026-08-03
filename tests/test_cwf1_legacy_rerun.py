"""CWF.1 — legacy backfill, rerun idempotency, and hydration integration tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.business_idea_validation.output_enrichment import enrich_output_commercial
from app.core.config import get_settings
from app.db.base import utc_now
from app.db.models.analysis_context import AnalysisContextTable
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.models.user_request import UserRequestTable
from app.schemas.contracts import (
    AnalysisContextState,
    BivResearchTerminalState,
    BusinessIdeaValidationRunRequest,
    BusinessIdeaValidationRunStatus,
    BusinessIdeaValidationVerdictKind,
)
from app.services.business_idea_validation_service import (
    RERUN_IDEMPOTENCY_PREFIX,
    BusinessIdeaValidationService,
    build_rerun_idempotency_key,
)
from tests.test_cwf_1a_launch_pack_decision import _output
from tests.test_product_01_3a_biv_intake_gate import (
    _seed_confirmed_context,
    _valid_fields,
)


def test_legacy_output_backfills_customer_report_from_risks() -> None:
    legacy = _output(
        BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        research_terminal_state=BivResearchTerminalState.SUCCEEDED_INSUFFICIENT,
    )
    assert legacy.customer_report is None
    enriched = enrich_output_commercial(legacy)
    assert enriched.customer_report is not None
    assert enriched.internal_diagnostics is not None
    assert enriched.customer_report.executive_summary.status_line


def test_rerun_idempotency_key_has_distinct_prefix() -> None:
    ctx = uuid4()
    key = build_rerun_idempotency_key(ctx, "a" * 64)
    assert key.startswith(RERUN_IDEMPOTENCY_PREFIX)


@pytest.mark.asyncio
async def test_get_latest_enriches_and_persists_legacy_run(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    request_id = uuid4()
    now = utc_now()
    legacy_output = _output(
        BusinessIdeaValidationVerdictKind.PROCEED,
        research_terminal_state=BivResearchTerminalState.SUCCEEDED_COMPLETE,
        analysis_context_id=confirmed.context_id,
        input_snapshot_hash=confirmed.input_snapshot_hash,
        project_id=project_id,
    )
    run_id = uuid4()
    db_session.add(
        UserRequestTable(
            id=request_id,
            owner_id=owner_id,
            tenant_id=owner_id,
            project_id=project_id,
            text=_valid_fields().idea_description,
            normalized_text=_valid_fields().idea_description,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        BusinessIdeaValidationRunTable(
            id=run_id,
            owner_id=owner_id,
            tenant_id=owner_id,
            user_request_id=request_id,
            project_id=project_id,
            investigation_id=uuid4(),
            analysis_context_id=confirmed.context_id,
            input_snapshot_hash=confirmed.input_snapshot_hash,
            idempotency_key="biv-research-legacy-key",
            status=BusinessIdeaValidationRunStatus.SUCCEEDED,
            result_json=legacy_output.model_dump(mode="json"),
            created_at=now,
            updated_at=now,
        )
    )
    ctx_row = await db_session.get(AnalysisContextTable, confirmed.context_id)
    assert ctx_row is not None
    ctx_row.state = AnalysisContextState.COMPLETED
    await db_session.commit()

    svc = BusinessIdeaValidationService(db_session, get_settings())
    latest = await svc.get_latest(owner_id, request_id)
    assert latest is not None
    assert latest.output is not None
    assert latest.output.customer_report is not None

    row = await svc._runs.get_by_id(run_id)  # noqa: SLF001
    assert row is not None
    assert row.result_json is not None
    assert row.result_json.get("customer_report") is not None


@pytest.mark.asyncio
async def test_project_hydration_backfills_legacy_run(db_session) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    request_id = uuid4()
    now = utc_now()
    legacy_output = _output(
        BusinessIdeaValidationVerdictKind.REVISE,
        research_terminal_state=BivResearchTerminalState.SUCCEEDED_INSUFFICIENT,
        analysis_context_id=confirmed.context_id,
        input_snapshot_hash=confirmed.input_snapshot_hash,
        project_id=project_id,
    )
    db_session.add(
        UserRequestTable(
            id=request_id,
            owner_id=owner_id,
            tenant_id=owner_id,
            project_id=project_id,
            text=_valid_fields().idea_description,
            normalized_text=_valid_fields().idea_description,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        BusinessIdeaValidationRunTable(
            id=uuid4(),
            owner_id=owner_id,
            tenant_id=owner_id,
            user_request_id=request_id,
            project_id=project_id,
            investigation_id=uuid4(),
            analysis_context_id=confirmed.context_id,
            input_snapshot_hash=confirmed.input_snapshot_hash,
            idempotency_key="biv-research-hydrate-key",
            status=BusinessIdeaValidationRunStatus.SUCCEEDED,
            result_json=legacy_output.model_dump(mode="json"),
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()

    svc = BusinessIdeaValidationService(db_session, get_settings())
    hydration = await svc.get_project_hydration(owner_id, project_id)
    assert hydration is not None
    assert hydration.output.customer_report is not None


@pytest.mark.asyncio
async def test_rerun_requires_rerun_idempotency_prefix(db_session) -> None:
    owner_id, _project_id, confirmed = await _seed_confirmed_context(db_session)
    request_id = uuid4()
    now = utc_now()
    db_session.add(
        UserRequestTable(
            id=request_id,
            owner_id=owner_id,
            tenant_id=owner_id,
            text=_valid_fields().idea_description,
            normalized_text=_valid_fields().idea_description,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()

    svc = BusinessIdeaValidationService(db_session, get_settings())
    with pytest.raises(Exception) as exc:
        await svc.run(
            owner_id,
            request_id,
            BusinessIdeaValidationRunRequest(
                idempotency_key=build_rerun_idempotency_key(
                    confirmed.context_id,
                    confirmed.input_snapshot_hash or "a" * 64,
                ).replace(RERUN_IDEMPOTENCY_PREFIX, "biv-research-"),
                analysis_context_id=confirmed.context_id,
                input_snapshot_hash=confirmed.input_snapshot_hash or "a" * 64,
                research_intent=True,
                rerun_intent=True,
            ),
        )
    assert "rerun_idempotency_key_required" in str(exc.value)


@pytest.mark.asyncio
async def test_rerun_creates_new_run_not_cache(db_session, monkeypatch) -> None:
    owner_id, project_id, confirmed = await _seed_confirmed_context(db_session)
    request_id = uuid4()
    now = utc_now()
    legacy_output = _output(
        BusinessIdeaValidationVerdictKind.PROCEED,
        research_terminal_state=BivResearchTerminalState.SUCCEEDED_COMPLETE,
        analysis_context_id=confirmed.context_id,
        input_snapshot_hash=confirmed.input_snapshot_hash,
        project_id=project_id,
    )
    old_run_id = uuid4()
    db_session.add(
        UserRequestTable(
            id=request_id,
            owner_id=owner_id,
            tenant_id=owner_id,
            project_id=project_id,
            text=_valid_fields().idea_description,
            normalized_text=_valid_fields().idea_description,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        BusinessIdeaValidationRunTable(
            id=old_run_id,
            owner_id=owner_id,
            tenant_id=owner_id,
            user_request_id=request_id,
            project_id=project_id,
            investigation_id=uuid4(),
            analysis_context_id=confirmed.context_id,
            input_snapshot_hash=confirmed.input_snapshot_hash,
            idempotency_key="biv-research-original-key",
            status=BusinessIdeaValidationRunStatus.SUCCEEDED,
            result_json=legacy_output.model_dump(mode="json"),
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()

    new_output = legacy_output.model_copy(
        update={
            "customer_report": enrich_output_commercial(legacy_output).customer_report,
        }
    )

    async def fake_skill_run(_self, _inp):
        return new_output

    from app.business_idea_validation import skill as skill_mod

    monkeypatch.setattr(skill_mod.BusinessIdeaValidationSkill, "run", fake_skill_run)

    svc = BusinessIdeaValidationService(db_session, get_settings())
    rerun_key = build_rerun_idempotency_key(
        confirmed.context_id,
        confirmed.input_snapshot_hash or "a" * 64,
    )
    response = await svc.run(
        owner_id,
        request_id,
        BusinessIdeaValidationRunRequest(
            idempotency_key=rerun_key,
            analysis_context_id=confirmed.context_id,
            input_snapshot_hash=confirmed.input_snapshot_hash or "a" * 64,
            research_intent=True,
            rerun_intent=True,
        ),
    )
    assert response.run_id != old_run_id
    assert response.output is not None
    assert response.output.customer_report is not None
    assert response.lineage_reused is False


def test_resolve_research_mode_rerun() -> None:
    from uuid import uuid4

    from app.schemas.contracts import BivResearchMode, BusinessIdeaValidationRunRequest
    from app.services.business_idea_validation_service import resolve_research_mode

    body = BusinessIdeaValidationRunRequest(
        idempotency_key="biv-rerun-abc-def",
        analysis_context_id=uuid4(),
        input_snapshot_hash="a" * 64,
        research_mode=BivResearchMode.INITIAL,
        rerun_intent=True,
    )
    assert resolve_research_mode(body) == BivResearchMode.RERUN


@pytest.mark.asyncio
async def test_double_rerun_same_key_returns_running_or_succeeded(db_session, monkeypatch) -> None:
    owner_id, _project_id, confirmed = await _seed_confirmed_context(db_session)
    request_id = uuid4()
    now = utc_now()
    db_session.add(
        UserRequestTable(
            id=request_id,
            owner_id=owner_id,
            tenant_id=owner_id,
            text=_valid_fields().idea_description,
            normalized_text=_valid_fields().idea_description,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()

    call_count = {"n": 0}
    legacy = _output(
        BusinessIdeaValidationVerdictKind.PROCEED,
        research_terminal_state=BivResearchTerminalState.SUCCEEDED_COMPLETE,
    )

    async def fake_skill_run(_self, _inp):
        call_count["n"] += 1
        return enrich_output_commercial(legacy)

    from app.business_idea_validation import skill as skill_mod

    monkeypatch.setattr(skill_mod.BusinessIdeaValidationSkill, "run", fake_skill_run)

    svc = BusinessIdeaValidationService(db_session, get_settings())
    rerun_key = build_rerun_idempotency_key(
        confirmed.context_id,
        confirmed.input_snapshot_hash or "a" * 64,
    )
    body = BusinessIdeaValidationRunRequest(
        idempotency_key=rerun_key,
        analysis_context_id=confirmed.context_id,
        input_snapshot_hash=confirmed.input_snapshot_hash or "a" * 64,
        research_intent=True,
        rerun_intent=True,
    )
    first = await svc.run(owner_id, request_id, body)
    second = await svc.run(owner_id, request_id, body)
    assert first.run_id == second.run_id
    assert call_count["n"] == 1


def test_api_research_idempotency_error_returns_commercial_envelope(
    client,
    auth_headers: dict[str, str],
) -> None:
    """409 domain codes must expose safe_message, never raw code as user copy."""
    from fastapi.testclient import TestClient

    assert isinstance(client, TestClient)
    req = client.post(
        "/user-requests",
        headers=auth_headers,
        json={"text": "Онлайн-школа для взрослых", "selected_scenario": "idea_validation"},
    )
    assert req.status_code == 201
    user_request_id = req.json()["id"]
    run = client.post(
        f"/user-requests/{user_request_id}/business-idea-validation/run",
        headers=auth_headers,
        json={
            "idempotency_key": "not-a-valid-research-key",
            "analysis_context_id": str(uuid4()),
            "input_snapshot_hash": "d" * 64,
            "research_intent": True,
        },
    )
    assert run.status_code == 409
    body = run.json()
    assert body.get("error_code") == "research_idempotency_key_required"
    safe = str(body.get("safe_message") or "")
    assert safe
    assert safe != "research_idempotency_key_required"
    assert "research_idempotency_key_required" not in safe
