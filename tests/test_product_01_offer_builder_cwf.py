"""PRODUCT-01 — Offer Builder runtime + CWF integration tests."""

from __future__ import annotations

import copy
from uuid import uuid4

import pytest
from app.connectors.evidence import hash_payload
from app.product.offer_builder.adapter import generate_offer_output
from app.product.offer_builder.contracts import (
    PACKAGE_HASH,
    SKILL_ID,
    OfferGenerationContext,
    UpstreamBundle,
)
from app.product.offer_builder.eligibility import evaluate_eligibility, map_biv_verdict_to_mv
from app.product.offer_builder.input_builder import build_skill_input, build_upstream_from_biv
from app.product.offer_builder.output_validation import (
    compute_output_hash,
    validate_output_schema,
    validate_output_semantics,
)
from app.schemas.contracts import (
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationVerdictKind,
    CommercialNextStepAction,
    LaunchPackOfferWorkflowStatus,
    LaunchPackRequestStatus,
    OfferApprovalStatus,
    OfferArtifactStatus,
    OfferGenerateRequest,
    OfferReviewDecisionCreate,
    OfferRevisionRequestCreate,
)
from fastapi.testclient import TestClient
from tests.support.archive_mkt_validation import (
    PACKAGE_HASHES,
    package_hash,
    validate_offer_output_semantics,
)
from tests.test_cwf_1a_launch_pack_decision import _output, _seed_launch_pack_context


def test_01_frozen_offer_builder_package_hash_unchanged() -> None:
    assert PACKAGE_HASHES[SKILL_ID] == PACKAGE_HASH
    assert package_hash(SKILL_ID) == PACKAGE_HASH


@pytest.mark.parametrize(
    ("verdict", "allowed"),
    [
        (BusinessIdeaValidationVerdictKind.PROCEED, True),
        (BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS, True),
        (BusinessIdeaValidationVerdictKind.REVISE, False),
        (BusinessIdeaValidationVerdictKind.REJECT, False),
        (BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE, False),
    ],
)
def test_eligibility_verdict_gates(verdict: BusinessIdeaValidationVerdictKind, allowed: bool) -> None:
    output = _output(verdict)
    upstream = build_upstream_from_biv(
        owner_id=uuid4(),
        project_id=uuid4(),
        output=output,
        accepted_conditions=["cond-a"] if verdict == BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS else [],
        mv_verdict=map_biv_verdict_to_mv(verdict),
    )
    result = evaluate_eligibility(biv_verdict=verdict, upstream=upstream)
    assert result.allowed is allowed


def test_proceed_with_conditions_inherits_conditions() -> None:
    output = _output(
        BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS,
        risks=[
            BusinessIdeaValidationRisk(
                title="Budget",
                description="Keep pilot budget under cap",
                severity="medium",
            )
        ],
    )
    upstream = build_upstream_from_biv(
        owner_id=uuid4(),
        project_id=uuid4(),
        output=output,
        accepted_conditions=["Budget: Keep pilot budget under cap"],
        mv_verdict="proceed_with_conditions",
    )
    assert len(upstream.inherited_conditions) >= 1
    skill_input = build_skill_input(upstream)
    assert skill_input["inherited_conditions"]


def test_missing_positioning_blocks() -> None:
    upstream = build_upstream_from_biv(
        owner_id=uuid4(),
        project_id=uuid4(),
        output=_output(BusinessIdeaValidationVerdictKind.PROCEED),
        accepted_conditions=[],
        mv_verdict="proceed",
    )
    broken = UpstreamBundle(
        market_validation=upstream.market_validation,
        positioning={},
        claim_substantiation=upstream.claim_substantiation,
        cim=upstream.cim,
        mv_verdict="proceed",
        positioning_hypothesis_id="hyp-primary",
        substantiated_claim_ids=upstream.substantiated_claim_ids,
    )
    result = evaluate_eligibility(
        biv_verdict=BusinessIdeaValidationVerdictKind.PROCEED,
        upstream=broken,
    )
    assert result.allowed is False
    assert result.blocker_code == "blocked_by_missing_positioning"


def test_missing_claims_blocks() -> None:
    upstream = build_upstream_from_biv(
        owner_id=uuid4(),
        project_id=uuid4(),
        output=_output(BusinessIdeaValidationVerdictKind.PROCEED),
        accepted_conditions=[],
        mv_verdict="proceed",
    )
    broken = UpstreamBundle(
        market_validation=upstream.market_validation,
        positioning=upstream.positioning,
        claim_substantiation={},
        cim=upstream.cim,
        mv_verdict="proceed",
        positioning_hypothesis_id="hyp-primary",
        substantiated_claim_ids=(),
    )
    result = evaluate_eligibility(
        biv_verdict=BusinessIdeaValidationVerdictKind.PROCEED,
        upstream=broken,
    )
    assert result.allowed is False
    assert result.blocker_code == "blocked_by_claims"


def test_missing_cim_blocks() -> None:
    upstream = build_upstream_from_biv(
        owner_id=uuid4(),
        project_id=uuid4(),
        output=_output(BusinessIdeaValidationVerdictKind.PROCEED),
        accepted_conditions=[],
        mv_verdict="proceed",
    )
    broken = UpstreamBundle(
        market_validation=upstream.market_validation,
        positioning=upstream.positioning,
        claim_substantiation=upstream.claim_substantiation,
        cim={"selected_segment_ids": []},
        mv_verdict="proceed",
        positioning_hypothesis_id="hyp-primary",
        substantiated_claim_ids=upstream.substantiated_claim_ids,
    )
    result = evaluate_eligibility(
        biv_verdict=BusinessIdeaValidationVerdictKind.PROCEED,
        upstream=broken,
    )
    assert result.allowed is False


def test_input_snapshot_deterministic() -> None:
    owner = uuid4()
    project = uuid4()
    output = _output(BusinessIdeaValidationVerdictKind.PROCEED)
    upstream = build_upstream_from_biv(
        owner_id=owner,
        project_id=project,
        output=output,
        accepted_conditions=[],
        mv_verdict="proceed",
    )
    a = hash_payload(build_skill_input(upstream))
    b = hash_payload(build_skill_input(upstream))
    assert a == b


def test_output_validates_against_frozen_schema() -> None:
    owner = uuid4()
    project = uuid4()
    output_biv = _output(BusinessIdeaValidationVerdictKind.PROCEED)
    upstream = build_upstream_from_biv(
        owner_id=owner,
        project_id=project,
        output=output_biv,
        accepted_conditions=[],
        mv_verdict="proceed",
    )
    ctx = OfferGenerationContext(
        owner_id=owner,
        project_id=project,
        launch_pack_request_id=uuid4(),
        business_verdict_id=output_biv.business_verdict_id or uuid4(),
        user_request_id=uuid4(),
        upstream=upstream,
        launch_objective="Test offer",
    )
    out = generate_offer_output(ctx)
    validate_output_schema(out)
    assert validate_output_semantics(out, mv_verdict="proceed", substantiated_claim_ids=set(upstream.substantiated_claim_ids)) == []


def test_unsupported_claim_cannot_become_proof() -> None:
    from tests.support.archive_mkt_validation import load_json_fixture, saas_catalog

    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_proceed_preferred.json")
    bad = copy.deepcopy(data)
    preferred = bad["offer_candidates"][0]
    preferred["claim_references"] = ["claim-not-substantiated"]
    preferred["status"] = "preferred"
    errors = validate_offer_output_semantics(
        bad,
        mv_verdict="proceed",
        substantiated_claim_ids=set(),
        cim_catalog=saas_catalog(),
    )
    assert len(errors) >= 1


def test_human_review_required_in_output() -> None:
    owner = uuid4()
    project = uuid4()
    output_biv = _output(BusinessIdeaValidationVerdictKind.PROCEED)
    upstream = build_upstream_from_biv(
        owner_id=owner,
        project_id=project,
        output=output_biv,
        accepted_conditions=[],
        mv_verdict="proceed",
    )
    ctx = OfferGenerationContext(
        owner_id=owner,
        project_id=project,
        launch_pack_request_id=uuid4(),
        business_verdict_id=output_biv.business_verdict_id or uuid4(),
        user_request_id=uuid4(),
        upstream=upstream,
    )
    out = generate_offer_output(ctx)
    assert out["human_approval_required"] is True
    assert "approval_granted" not in out


def test_output_hash_deterministic() -> None:
    owner = uuid4()
    project = uuid4()
    launch = uuid4()
    verdict = uuid4()
    request = uuid4()
    output_biv = _output(BusinessIdeaValidationVerdictKind.PROCEED, business_verdict_id=verdict)
    upstream = build_upstream_from_biv(
        owner_id=owner,
        project_id=project,
        output=output_biv,
        accepted_conditions=[],
        mv_verdict="proceed",
    )
    ctx = OfferGenerationContext(
        owner_id=owner,
        project_id=project,
        launch_pack_request_id=launch,
        business_verdict_id=verdict,
        user_request_id=request,
        upstream=upstream,
        launch_objective="Same objective",
    )
    a = generate_offer_output(ctx)
    b = generate_offer_output(ctx)
    assert a["output_hash"] == b["output_hash"]
    assert compute_output_hash({k: v for k, v in a.items() if k != "output_hash"}) == a["output_hash"]


@pytest.mark.asyncio
async def test_offer_generation_persisted(db_session) -> None:
    from app.core.config import get_settings
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    result = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-persist-key",
        ),
    )
    assert result.launch_pack_request is not None
    assert result.offer is not None
    assert result.offer.offer_title
    assert result.offer.status == OfferArtifactStatus.REVIEW_REQUIRED
    assert result.launch_pack_request.offer_workflow_status == LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED


@pytest.mark.asyncio
async def test_idempotent_generation_no_duplicate(db_session) -> None:
    from app.core.config import get_settings
    from app.db.repositories.offer_artifacts import OfferArtifactRepository
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    body = CommercialNextStepDecisionCreate(
        selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
        idempotency_key="product01-idem-key",
    )
    first = await lp.submit_next_step(owner_id, project_id, body)
    launch_id = first.launch_pack_request.id if first.launch_pack_request else None
    assert launch_id is not None
    offer_svc = OfferBuilderService(db_session, get_settings())
    again = await offer_svc.generate_for_launch_pack(
        owner_id,
        project_id,
        launch_id,
        OfferGenerateRequest(idempotency_key=f"offer-{launch_id}-product01-idem-key"),
    )
    assert again.lineage_reused is True
    repo = OfferArtifactRepository(db_session)
    artifact = await repo.get_by_launch_pack(owner_id, launch_id)
    versions = await repo.list_versions(artifact.id)
    assert len(versions) == 1


@pytest.mark.asyncio
async def test_approve_exact_version(db_session) -> None:
    from app.core.config import get_settings
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    created = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-approve-key",
        ),
    )
    assert created.offer is not None
    offer_svc = OfferBuilderService(db_session, get_settings())
    approved = await offer_svc.approve(
        owner_id,
        created.offer.id,
        OfferReviewDecisionCreate(expected_output_hash=created.offer.output_hash),
    )
    assert approved.approval_status == OfferApprovalStatus.APPROVED
    assert approved.status == OfferArtifactStatus.APPROVED
    journey = await lp.get_journey(owner_id, project_id)
    assert journey is not None
    assert journey.launch_pack_request is not None
    assert journey.launch_pack_request.offer_workflow_status == LaunchPackOfferWorkflowStatus.OFFER_APPROVED
    assert journey.launch_pack_request.status != LaunchPackRequestStatus.READY


@pytest.mark.asyncio
async def test_stale_hash_approval_fails(db_session) -> None:
    from app.core.config import get_settings
    from app.core.exceptions import InvalidStateError
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    created = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-stale-key",
        ),
    )
    assert created.offer is not None
    offer_svc = OfferBuilderService(db_session, get_settings())
    with pytest.raises(InvalidStateError, match="stale_approval_hash"):
        await offer_svc.approve(
            owner_id,
            created.offer.id,
            OfferReviewDecisionCreate(expected_output_hash="0" * 64),
        )


@pytest.mark.asyncio
async def test_revision_creates_new_version(db_session) -> None:
    from app.core.config import get_settings
    from app.db.repositories.offer_artifacts import OfferArtifactRepository
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    created = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-revision-key",
        ),
    )
    assert created.offer is not None
    offer_svc = OfferBuilderService(db_session, get_settings())
    revised = await offer_svc.request_revision(
        owner_id,
        created.offer.id,
        OfferRevisionRequestCreate(
            expected_output_hash=created.offer.output_hash,
            comment="Clarify pricing",
        ),
    )
    assert revised.version_number == 2
    repo = OfferArtifactRepository(db_session)
    versions = await repo.list_versions(created.offer.id)
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[1].status == OfferArtifactStatus.REVISION_REQUESTED


@pytest.mark.asyncio
async def test_cross_tenant_offer_not_found(db_session) -> None:
    from app.core.config import get_settings
    from app.core.exceptions import NotFoundError
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService
    from tests.conftest import _create_user_with_api_key

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    created = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-tenant-key",
        ),
    )
    assert created.offer is not None
    _key, other_user = await _create_user_with_api_key()
    offer_svc = OfferBuilderService(db_session, get_settings())
    with pytest.raises(NotFoundError):
        await offer_svc.get_offer(other_user.id, created.offer.id)


def test_offer_api_404_unknown_offer(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id = uuid4()
    offer_id = uuid4()
    resp = client.get(f"/projects/{project_id}/offers/{offer_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_insufficient_evidence_blocks_offer_via_api(
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

    project_id = uuid4()
    output = _output(BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE)
    hydration = BusinessIdeaValidationProjectHydration(
        project_id=project_id,
        user_request_id=uuid4(),
        user_request_text="Test",
        run_id=uuid4(),
        status=BusinessIdeaValidationRunStatus.SUCCEEDED,
        output=output,
        updated_at=datetime.utcnow(),
    )

    async def fake_hydration(_self, _owner_id, _project_id):
        return hydration

    monkeypatch.setattr(BusinessIdeaValidationService, "get_project_hydration", fake_hydration)

    submit = client.post(
        f"/projects/{project_id}/launch-pack/next-step",
        headers=auth_headers,
        json={
            "selected_action": "prepare_launch",
            "idempotency_key": "product01-insufficient-key",
        },
    )
    assert submit.status_code == 400


def test_kb_wpl_frozen_hashes_unchanged() -> None:
    from tests.support.kb_wpl_program_validation import load_hash_registry

    registry = load_hash_registry()
    skill_packages = registry.get("hashes", {}).get("skill_packages", {})
    assert SKILL_ID not in skill_packages
    assert package_hash(SKILL_ID) == PACKAGE_HASH


def test_alembic_migration_revision_chain() -> None:
    import importlib.util
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260724_0059_offer_builder_product_01.py"
    )
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("offer_migration", migration_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "20260724_0059"
    assert module.down_revision == "20260723_0058"
    source = migration_path.read_text(encoding="utf-8")
    for table in (
        "offer_artifacts",
        "offer_artifact_versions",
        "offer_review_events",
        "commercial_upstream_snapshots",
    ):
        assert table in source
    for column in ("source_mode", "bridge_version", "replacement_required"):
        assert column in source


def test_bridged_upstream_labeled_in_skill_input() -> None:
    from app.schemas.contracts import UpstreamSourceMode

    output = _output(BusinessIdeaValidationVerdictKind.PROCEED)
    upstream = build_upstream_from_biv(
        owner_id=uuid4(),
        project_id=uuid4(),
        output=output,
        accepted_conditions=[],
        mv_verdict="proceed",
    )
    skill_input = build_skill_input(upstream)
    for ref_key in (
        "source_positioning_reference",
        "source_claim_substantiation_reference",
        "source_market_validation_reference",
    ):
        ref = skill_input[ref_key]
        assert ref["source_mode"] == UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT.value
        assert ref["replacement_required"] is True
        assert ref["bridge_version"]


@pytest.mark.asyncio
async def test_bridged_snapshots_persisted_not_native(db_session) -> None:
    from app.core.config import get_settings
    from app.db.repositories.offer_artifacts import OfferArtifactRepository
    from app.schemas.contracts import CommercialNextStepDecisionCreate, UpstreamSourceMode
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    result = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-bridge-key",
        ),
    )
    assert result.offer is not None
    for source in result.offer.upstream_sources:
        assert source.source_mode == UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT
        assert source.replacement_required is True
        assert source.bridge_version
        assert source.source_mode != UpstreamSourceMode.NATIVE_SKILL_OUTPUT

    repo = OfferArtifactRepository(db_session)
    rows = await repo.list_upstream_snapshots(result.launch_pack_request.id)
    assert len(rows) == 4
    assert all(row.source_mode == UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT for row in rows)


@pytest.mark.asyncio
async def test_invalid_workflow_transition_returns_409(db_session) -> None:
    from app.core.config import get_settings
    from app.core.exceptions import InvalidStateError
    from app.db.repositories.launch_pack_requests import LaunchPackRequestRepository
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import (
        CommercialNextStepDecisionCreate,
        OfferReviewDecisionCreate,
    )
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    created = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-invalid-transition",
        ),
    )
    assert created.offer is not None
    launch_repo = LaunchPackRequestRepository(db_session)
    launch = await launch_repo.get_by_id(owner_id, created.launch_pack_request.id)
    assert launch is not None
    launch.offer_workflow_status = LaunchPackOfferWorkflowStatus.OFFER_REJECTED.value
    offer_svc = OfferBuilderService(db_session, get_settings())
    with pytest.raises(InvalidStateError, match="invalid_workflow_transition"):
        await offer_svc.approve(
            owner_id,
            created.offer.id,
            OfferReviewDecisionCreate(expected_output_hash=created.offer.output_hash),
        )


@pytest.mark.asyncio
async def test_concurrent_generation_idempotent(db_session) -> None:
    import asyncio

    from app.core.config import get_settings
    from app.db.repositories.offer_artifacts import OfferArtifactRepository
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    first = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-concurrent-gen",
        ),
    )
    launch_id = first.launch_pack_request.id if first.launch_pack_request else None
    assert launch_id is not None
    offer_svc = OfferBuilderService(db_session, get_settings())
    idem = f"offer-{launch_id}-product01-concurrent-gen"

    async def _regen() -> None:
        await offer_svc.generate_for_launch_pack(
            owner_id,
            project_id,
            launch_id,
            OfferGenerateRequest(idempotency_key=idem),
        )

    await asyncio.gather(_regen(), _regen())
    repo = OfferArtifactRepository(db_session)
    artifact = await repo.get_by_launch_pack(owner_id, launch_id)
    assert artifact is not None
    versions = await repo.list_versions(artifact.id)
    assert len(versions) == 1


@pytest.mark.asyncio
async def test_repeated_approve_idempotent(db_session) -> None:
    from app.core.config import get_settings
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate, OfferReviewDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    created = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-concurrent-approve",
        ),
    )
    assert created.offer is not None
    offer_svc = OfferBuilderService(db_session, get_settings())
    body = OfferReviewDecisionCreate(expected_output_hash=created.offer.output_hash)
    first = await offer_svc.approve(owner_id, created.offer.id, body)
    second = await offer_svc.approve(owner_id, created.offer.id, body)
    assert first.approval_status == OfferApprovalStatus.APPROVED
    assert second.approval_status == OfferApprovalStatus.APPROVED
    assert first.output_hash == second.output_hash
    import asyncio

    from app.core.config import get_settings
    from app.db.repositories.offer_artifacts import OfferArtifactRepository
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    first = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-concurrent-gen",
        ),
    )
    launch_id = first.launch_pack_request.id if first.launch_pack_request else None
    assert launch_id is not None
    offer_svc = OfferBuilderService(db_session, get_settings())
    idem = f"offer-{launch_id}-product01-concurrent-gen"

    async def _regen() -> None:
        await offer_svc.generate_for_launch_pack(
            owner_id,
            project_id,
            launch_id,
            OfferGenerateRequest(idempotency_key=idem),
        )

    await asyncio.gather(_regen(), _regen())
    repo = OfferArtifactRepository(db_session)
    artifact = await repo.get_by_launch_pack(owner_id, launch_id)
    assert artifact is not None
    versions = await repo.list_versions(artifact.id)
    assert len(versions) == 1


@pytest.mark.asyncio
async def test_recovery_from_stuck_building_offer(db_session) -> None:
    from app.core.config import get_settings
    from app.db.repositories.launch_pack_requests import LaunchPackRequestRepository
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    created = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-recover-key",
        ),
    )
    assert created.offer is not None
    launch_repo = LaunchPackRequestRepository(db_session)
    launch = await launch_repo.get_by_id(owner_id, created.launch_pack_request.id)
    assert launch is not None
    launch.offer_workflow_status = LaunchPackOfferWorkflowStatus.BUILDING_OFFER.value
    offer_svc = OfferBuilderService(db_session, get_settings())
    recovered = await offer_svc.recover(owner_id, created.offer.id)
    assert recovered.launch_pack_workflow_status == LaunchPackOfferWorkflowStatus.OFFER_REVIEW_REQUIRED
    assert recovered.offer.status == OfferArtifactStatus.REVIEW_REQUIRED


@pytest.mark.asyncio
async def test_reload_hydration_canonical(db_session) -> None:
    from app.core.config import get_settings
    from app.product.offer_builder.service import OfferBuilderService
    from app.schemas.contracts import CommercialNextStepDecisionCreate, OfferReviewDecisionCreate
    from app.services.launch_pack_service import LaunchPackService

    owner_id, project_id, _req, _out = await _seed_launch_pack_context(
        db_session,
        verdict=BusinessIdeaValidationVerdictKind.PROCEED,
    )
    lp = LaunchPackService(db_session, get_settings())
    created = await lp.submit_next_step(
        owner_id,
        project_id,
        CommercialNextStepDecisionCreate(
            selected_action=CommercialNextStepAction.PREPARE_LAUNCH,
            idempotency_key="product01-reload-key",
        ),
    )
    assert created.offer is not None
    offer_svc = OfferBuilderService(db_session, get_settings())
    approved = await offer_svc.approve(
        owner_id,
        created.offer.id,
        OfferReviewDecisionCreate(expected_output_hash=created.offer.output_hash),
    )
    reloaded = await offer_svc.get_offer(owner_id, created.offer.id)
    assert reloaded.approval_status == OfferApprovalStatus.APPROVED
    assert reloaded.output_hash == approved.output_hash
    assert reloaded.version_number == approved.version_number
    assert len(reloaded.upstream_sources) == 4


def test_recover_endpoint_maps_conflict(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    resp = client.post(
        f"/projects/{uuid4()}/offers/{uuid4()}/recover",
        headers=auth_headers,
    )
    assert resp.status_code in {404, 409}
