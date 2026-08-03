"""CWF.1a — verdict decision branch + Launch Pack request tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.commercial_workflow.decision_branch import (
    build_decision_branch,
    launch_pack_allowed_for_action,
)
from app.schemas.contracts import (
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationVerdictKind,
    CommercialNextStepAction,
    LaunchPackRequestStatus,
)
from fastapi.testclient import TestClient


def _output(verdict: BusinessIdeaValidationVerdictKind, **kwargs) -> BusinessIdeaValidationOutput:
    defaults = dict(
        investigation_id=uuid4(),
        business_verdict_id=uuid4(),
        verdict=verdict,
        confidence=BusinessIdeaValidationConfidence(total_score=55),
        findings=[],
        risks=[
            BusinessIdeaValidationRisk(
                title="Risk X",
                description="Reduce budget exposure",
                severity="high",
            )
        ],
        limitations=["Need clearer audience"],
    )
    defaults.update(kwargs)
    return BusinessIdeaValidationOutput(**defaults)


@pytest.mark.parametrize(
    ("verdict", "allowed", "primary_action"),
    [
        (BusinessIdeaValidationVerdictKind.PROCEED, True, CommercialNextStepAction.PREPARE_LAUNCH),
        (
            BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS,
            True,
            CommercialNextStepAction.PREPARE_LAUNCH,
        ),
        (BusinessIdeaValidationVerdictKind.REVISE, False, CommercialNextStepAction.REVISE_IDEA),
        (BusinessIdeaValidationVerdictKind.REJECT, False, CommercialNextStepAction.REQUEST_ALTERNATIVE),
        (
            BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
            False,
            CommercialNextStepAction.REFINE_INPUTS,
        ),
    ],
)
def test_decision_branch_mapping(verdict, allowed, primary_action) -> None:
    branch = build_decision_branch(_output(verdict))
    assert branch.verdict == verdict
    assert branch.launch_pack_allowed is allowed
    assert branch.primary_cta is not None
    assert branch.primary_cta.action == primary_action
    assert len(branch.launch_pack_included_keys) == 7
    assert len(branch.launch_pack_excluded_keys) == 5


def test_proceed_with_conditions_requires_acceptance() -> None:
    output = _output(BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS)
    branch = build_decision_branch(output)
    assert branch.primary_cta is not None
    assert branch.primary_cta.requires_conditions_acceptance is True
    assert not launch_pack_allowed_for_action(
        branch,
        CommercialNextStepAction.PREPARE_LAUNCH,
        accepted_conditions=[],
        override_reason=None,
    )
    assert launch_pack_allowed_for_action(
        branch,
        CommercialNextStepAction.PREPARE_LAUNCH,
        accepted_conditions=branch.conditions,
        override_reason=None,
    )


def test_revise_requires_override_for_prepare_launch() -> None:
    output = _output(BusinessIdeaValidationVerdictKind.REVISE)
    branch = build_decision_branch(output)
    assert not launch_pack_allowed_for_action(
        branch,
        CommercialNextStepAction.PREPARE_LAUNCH,
        accepted_conditions=[],
        override_reason=None,
    )
    assert launch_pack_allowed_for_action(
        branch,
        CommercialNextStepAction.PREPARE_LAUNCH,
        accepted_conditions=[],
        override_reason="Owner accepts risk",
    )


def test_launch_pack_api_blocked_for_insufficient_evidence(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import datetime

    from app.schemas.contracts import (
        BusinessIdeaValidationProjectHydration,
        BusinessIdeaValidationRunStatus,
        LaunchPackJourneyHydration,
    )
    from app.services.business_idea_validation_service import BusinessIdeaValidationService
    from app.services.launch_pack_service import LaunchPackService

    project_id = uuid4()
    output = _output(BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE)
    branch = build_decision_branch(output)
    hydration = LaunchPackJourneyHydration(
        project_id=project_id,
        user_request_id=uuid4(),
        user_request_text="Test idea",
        validation=BusinessIdeaValidationProjectHydration(
            project_id=project_id,
            user_request_id=uuid4(),
            user_request_text="Test idea",
            run_id=uuid4(),
            status=BusinessIdeaValidationRunStatus.SUCCEEDED,
            output=output,
            updated_at=datetime.utcnow(),
        ),
        decision_branch=branch,
        updated_at=datetime.utcnow(),
    )

    async def fake_journey(_self, _owner_id, _project_id):
        return hydration

    async def fake_hydration(_self, _owner_id, _project_id):
        return hydration.validation

    monkeypatch.setattr(LaunchPackService, "get_journey", fake_journey)
    monkeypatch.setattr(BusinessIdeaValidationService, "get_project_hydration", fake_hydration)

    resp = client.get(f"/projects/{project_id}/launch-pack/journey", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision_branch"]["launch_pack_allowed"] is False

    submit = client.post(
        f"/projects/{project_id}/launch-pack/next-step",
        headers=auth_headers,
        json={
            "selected_action": "prepare_launch",
            "idempotency_key": "cwf1a-blocked-test-key",
        },
    )
    assert submit.status_code == 400
    submit_body = submit.json()
    assert submit_body.get("safe_message") == "action_not_allowed_for_verdict" or submit_body.get(
        "detail"
    ) == "action_not_allowed_for_verdict"


@pytest.mark.asyncio
async def test_launch_pack_service_proceed_requested(db_session) -> None:
    from app.core.config import get_settings
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _request_id, _output = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    svc = LaunchPackService(db_session, get_settings())
    result = await svc.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="cwf1a-service-proceed-key",
        ),
    )
    assert result.launch_pack_request is not None
    assert result.launch_pack_request.status in {
        LaunchPackRequestStatus.REQUESTED,
        LaunchPackRequestStatus.IN_PROGRESS,
    }


@pytest.mark.asyncio
async def test_launch_pack_service_idempotent(db_session) -> None:
    from app.core.config import get_settings
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _request_id, _output = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    svc = LaunchPackService(db_session, get_settings())
    body = CommercialNextStepDecisionCreate(
        selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
        idempotency_key="cwf1a-service-idem-key",
    )
    first = await svc.submit_next_step(owner_id, project_id, body)
    second = await svc.submit_next_step(owner_id, project_id, body)
    assert second.lineage_reused is True
    assert first.launch_pack_request is not None
    assert second.launch_pack_request is not None
    assert first.launch_pack_request.id == second.launch_pack_request.id


async def _seed_launch_pack_context(db_session, *, verdict: BusinessIdeaValidationVerdictKind):
    from app.db.base import utc_now
    from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
    from app.db.models.business_verdict import (
        BusinessVerdictEvidenceSnapshotTable,
        BusinessVerdictTable,
    )
    from app.db.models.investigation import InvestigationTable
    from app.db.models.project import ProjectTable
    from app.db.models.project_brief import ProjectBriefTable
    from app.db.models.user_request import UserRequestTable
    from app.schemas.contracts import (
        BusinessIdeaValidationRunStatus,
        BusinessVerdictConfidenceLevel,
        BusinessVerdictLifecycleStatus,
        BusinessVerdictPreparedByType,
        VerdictKind,
        VerdictReadinessStatus,
    )
    from tests.conftest import _create_user_with_api_key

    _key, user = await _create_user_with_api_key()
    owner_id = user.id
    now = utc_now()
    project_id = uuid4()
    brief_id = uuid4()
    investigation_id = uuid4()
    snapshot_id = uuid4()
    verdict_id = uuid4()
    request_id = uuid4()

    db_session.add(
        ProjectTable(
            id=project_id,
            owner_id=owner_id,
            name="CWF test project",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        ProjectBriefTable(
            id=brief_id,
            owner_id=owner_id,
            project_id=project_id,
            version=1,
            input_fingerprint="fp-test",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        InvestigationTable(
            id=investigation_id,
            owner_id=owner_id,
            project_id=project_id,
            project_brief_id=brief_id,
            project_brief_version=1,
            input_fingerprint="inv-fp-test",
            version=1,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        BusinessVerdictEvidenceSnapshotTable(
            id=snapshot_id,
            owner_id=owner_id,
            project_id=project_id,
            investigation_id=investigation_id,
            snapshot_hash="hash-" + str(snapshot_id)[:8],
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        BusinessVerdictTable(
            id=verdict_id,
            owner_id=owner_id,
            project_id=project_id,
            investigation_id=investigation_id,
            investigation_version=1,
            project_brief_id=brief_id,
            project_brief_version=1,
            version=1,
            verdict_type=VerdictKind.CONDITIONAL_GO,
            lifecycle_status=BusinessVerdictLifecycleStatus.DRAFT,
            confidence_level=BusinessVerdictConfidenceLevel.MEDIUM,
            evidence_snapshot_id=snapshot_id,
            evidence_snapshot_hash="hash-" + str(snapshot_id)[:8],
            executive_conclusion="Proceed",
            executive_rationale="Evidence supports launch",
            primary_business_implication="Test",
            recommended_next_action="Prepare launch",
            readiness_snapshot=VerdictReadinessStatus.READY_FOR_REVIEW,
            prepared_by_type=BusinessVerdictPreparedByType.DETERMINISTIC,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        UserRequestTable(
            id=request_id,
            owner_id=owner_id,
            text="Coffee shop take-away idea",
            project_id=project_id,
            created_at=now,
            updated_at=now,
        )
    )
    output = _output(verdict, business_verdict_id=verdict_id)
    db_session.add(
        BusinessIdeaValidationRunTable(
            owner_id=owner_id,
            tenant_id=owner_id,
            user_request_id=request_id,
            project_id=project_id,
            investigation_id=investigation_id,
            business_verdict_id=verdict_id,
            idempotency_key=f"seed-{uuid4()}",
            status=BusinessIdeaValidationRunStatus.SUCCEEDED,
            result_json=output.model_dump(mode="json"),
            created_at=now,
            updated_at=now,
            finished_at=now,
        )
    )
    await db_session.commit()
    return owner_id, project_id, request_id, output


def test_launch_pack_journey_not_found_for_other_tenant(
    client: TestClient,
    other_auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.business_idea_validation_service import BusinessIdeaValidationService

    project_id = uuid4()

    async def fake_hydration(_self, _owner_id, _project_id):
        return None

    monkeypatch.setattr(BusinessIdeaValidationService, "get_project_hydration", fake_hydration)

    resp = client.get(f"/projects/{project_id}/launch-pack/journey", headers=other_auth_headers)
    assert resp.status_code == 404
