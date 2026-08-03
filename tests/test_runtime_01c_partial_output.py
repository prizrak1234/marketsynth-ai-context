"""RUNTIME-01C — partial research output on evidence-insufficiency failures."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.business_idea_validation.output_enrichment import enrich_output_commercial
from app.business_idea_validation.partial_research_delivery import (
    EVIDENCE_INSUFFICIENCY_CODES,
    PartialResearchBuildContext,
    build_partial_research_output,
    can_deliver_partial_research,
    is_partial_research_output,
)
from app.business_idea_validation.skill import BusinessIdeaValidationSkill
from app.core.config import get_settings
from app.core.exceptions import ResearchPipelineError
from app.db.models.business_idea_validation_run import BusinessIdeaValidationRunTable
from app.db.models.analysis_context import AnalysisContextTable
from app.db.session import get_session_factory
from app.main import app
from app.schemas.contracts import (
    AnalysisContextConfirmRequest,
    AnalysisContextCreateDraftRequest,
    AnalysisContextState,
    BivDiscoveryMetrics,
    BivEvidenceItem,
    BivEvidenceStageMetrics,
    BivExtractMetrics,
    BivFetchStageMetrics,
    BivFindingItem,
    BivPartialResearchReport,
    BivPipelineMetrics,
    BivResearchResultKind,
    BivResearchTerminalState,
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationRunStatus,
    ResearchCoveragePlan,
)
from app.services.business_idea_validation_service import (
    build_research_idempotency_key,
    build_rerun_idempotency_key,
)
from tests.conftest import _create_user_with_api_key

IDEA = (
    "AI-платформа для автоматического создания коммерческих "
    "предложений для строительных компаний"
)


def _accepted_evidence(category: str = "market") -> BivEvidenceItem:
    return BivEvidenceItem(
        evidence_id=uuid4(),
        source_url="https://example.com/market-report",
        source_title="Market report",
        accessed_at=datetime.now(UTC),
        excerpt="Substantive market observation with enough detail for validation.",
        claim_supported="Market demand signal for construction SaaS.",
        relevance_score=0.8,
        quality_score=0.7,
        freshness_score=0.6,
        independence_group="example.com",
        category=category,
        accepted=True,
    )


def _finding_item(evidence_id: UUID | None = None) -> BivFindingItem:
    eid = evidence_id or uuid4()
    return BivFindingItem(
        finding_id=uuid4(),
        category="market",
        claim="Demand exists in construction SaaS",
        interpretation="Early demand signal is visible",
        business_impact="Supports pilot validation",
        evidence_ids=[eid],
        confidence=0.6,
    )


def _executed_metrics() -> BivPipelineMetrics:
    return BivPipelineMetrics(
        discovery=BivDiscoveryMetrics(search_success_count=2),
        fetch=BivFetchStageMetrics(fetch_success_count=1),
        extract=BivExtractMetrics(extraction_success_count=1),
        evidence=BivEvidenceStageMetrics(accepted_evidence=1, evidence_candidates=2),
    )


def _partial_output(**kwargs) -> BusinessIdeaValidationOutput:
    evidence_item = _accepted_evidence()
    ctx = PartialResearchBuildContext(
        investigation_id=uuid4(),
        partial_report=BivPartialResearchReport(
            established_findings=["Рынок строительных SaaS растёт"],
            interim_conclusion="Недостаточно данных для полного вердикта.",
        ),
        evidence_items=[evidence_item],
        finding_items=[_finding_item(evidence_item.evidence_id)],
        sources=[],
        evidence=[],
        findings=[],
        risks=[],
        opportunities=[],
        research_plan=[],
        coverage_plan=ResearchCoveragePlan(),
        research_gaps=["high_impact_insufficient_sources"],
        research_gap_items=[],
        semantic_gap_groups=[],
        remediation_questions=[],
        category_coverage=[],
        research_stop_reason=None,
        confidence=BusinessIdeaValidationConfidence(total_score=42),
        limitations=["Недостаточно источников высокого impact"],
        mcp_search_calls=1,
        mcp_fetch_calls=1,
        research_rounds_completed=1,
    )
    output = build_partial_research_output(
        ctx,
        failure_code="high_impact_insufficient_sources",
        safe_message="Недостаточно источников для полного вердикта.",
    )
    return output.model_copy(update=kwargs)


async def _seed_biv_request(client: AsyncClient, headers: dict[str, str]) -> dict:
    project = await client.post("/projects", json={"name": "RUNTIME-01C"}, headers=headers)
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


@pytest.fixture
def biv_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUSINESS_IDEA_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("MCP_READ_ONLY_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "true")
    monkeypatch.setenv("BIV_RUN_DISPATCHER_ENABLED", "true")
    get_settings.cache_clear()


def test_whitelist_contains_only_confirmed_codes() -> None:
    assert EVIDENCE_INSUFFICIENCY_CODES == frozenset(
        {
            "high_impact_insufficient_sources",
            "finding_without_evidence",
            "finding_unaccepted_evidence",
            "finding_uses_rejected_evidence",
            "citation_coverage_incomplete",
        }
    )
    assert "category_floor_insufficient" not in EVIDENCE_INSUFFICIENCY_CODES


def test_can_deliver_partial_requires_whitelist_and_artifacts() -> None:
    metrics = _executed_metrics()
    partial_report = BivPartialResearchReport(established_findings=["Signal"])
    evidence = [_accepted_evidence()]
    assert can_deliver_partial_research(
        "high_impact_insufficient_sources",
        metrics=metrics,
        partial_report=partial_report,
        evidence_items=evidence,
        finding_items=[],
    )
    assert not can_deliver_partial_research(
        "high_impact_insufficient_sources",
        metrics=metrics,
        partial_report=None,
        evidence_items=[],
        finding_items=[],
    )
    assert not can_deliver_partial_research(
        "category_floor_insufficient:market",
        metrics=metrics,
        partial_report=partial_report,
        evidence_items=evidence,
        finding_items=[],
    )
    assert not can_deliver_partial_research(
        "pipeline_fetch_failed",
        metrics=metrics,
        partial_report=partial_report,
        evidence_items=evidence,
        finding_items=[],
    )
    assert not can_deliver_partial_research(
        "high_impact_insufficient_sources",
        metrics=BivPipelineMetrics(),
        partial_report=partial_report,
        evidence_items=evidence,
        finding_items=[],
    )


def test_build_partial_output_contract() -> None:
    output = _partial_output()
    assert output.research_terminal_state == BivResearchTerminalState.SUCCEEDED_INSUFFICIENT
    assert output.result_kind == BivResearchResultKind.PARTIAL_RESEARCH
    assert output.partial_report is not None
    assert output.customer_report is None
    assert output.commercial_verdict is None
    assert output.business_verdict_id is None
    assert is_partial_research_output(output)


def test_enrichment_does_not_create_customer_report_for_partial() -> None:
    output = _partial_output()
    enriched = enrich_output_commercial(output)
    assert enriched.customer_report is None
    assert enriched.commercial_verdict is None
    assert enriched.result_kind == BivResearchResultKind.PARTIAL_RESEARCH


@pytest.mark.asyncio
async def test_runtime_01c_async_partial_output_persisted(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def partial_run(self, inp, **kwargs):
        return _partial_output()

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", partial_run)

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
        run_id = UUID(resp.json()["run_id"])

        row = None
        factory = get_session_factory()
        for _ in range(100):
            async with factory() as session:
                row = await session.get(BusinessIdeaValidationRunTable, run_id)
                assert row is not None
                if row.status == BusinessIdeaValidationRunStatus.FAILED and row.result_json:
                    break
            await asyncio.sleep(0.05)

        assert row is not None
        assert row.status == BusinessIdeaValidationRunStatus.FAILED
        assert row.error_code == "high_impact_insufficient_sources"
        assert row.result_json is not None
        assert row.result_json["result_kind"] == "partial_research"
        assert row.result_json["research_terminal_state"] == "succeeded_insufficient"
        assert row.result_json["customer_report"] is None
        assert row.result_json["commercial_verdict"] is None
        assert row.result_json["business_verdict_id"] is None

        get_resp = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}",
            headers=headers,
        )
        assert get_resp.status_code == 200, get_resp.text
        body = get_resp.json()
        assert body["status"] == "failed"
        assert body["output"] is not None
        assert body["output"]["result_kind"] == "partial_research"
        assert body["output"]["customer_report"] is None

        async with factory() as session:
            ctx_row = await session.get(AnalysisContextTable, UUID(seeded["context_id"]))
            assert ctx_row is not None
            assert ctx_row.state == AnalysisContextState.CONFIRMED

        rerun_key = build_rerun_idempotency_key(
            UUID(seeded["context_id"]),
            seeded["snapshot_hash"],
        )
        rerun_resp = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs",
            json={
                **seeded["run_body"],
                "idempotency_key": rerun_key,
                "rerun_intent": True,
            },
            headers=headers,
        )
        assert rerun_resp.status_code == 202, rerun_resp.text


@pytest.mark.asyncio
async def test_runtime_01c_pipeline_error_without_partial_keeps_output_null(
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
        run_id = UUID(resp.json()["run_id"])
        factory = get_session_factory()
        row = None
        for _ in range(100):
            async with factory() as session:
                row = await session.get(BusinessIdeaValidationRunTable, run_id)
                assert row is not None
                if row.status == BusinessIdeaValidationRunStatus.FAILED:
                    break
            await asyncio.sleep(0.05)

        assert row is not None
        assert row.result_json is None

        get_resp = await client.get(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/runs/{run_id}",
            headers=headers,
        )
        assert get_resp.json()["output"] is None


@pytest.mark.asyncio
async def test_runtime_01c_sync_partial_output_contract(
    db_session,
    biv_runtime_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def partial_run(self, inp, **kwargs):
        return _partial_output()

    monkeypatch.setattr(BusinessIdeaValidationSkill, "run", partial_run)

    api_key, _user = await _create_user_with_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seeded = await _seed_biv_request(client, headers)
        resp = await client.post(
            f"/user-requests/{seeded['request_id']}/business-idea-validation/run",
            json=seeded["run_body"],
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "failed"
        assert body["error_code"] == "high_impact_insufficient_sources"
        assert body["output"] is not None
        assert body["output"]["result_kind"] == "partial_research"
        assert body["output"]["customer_report"] is None
        assert body["output"]["commercial_verdict"] is None


@pytest.mark.asyncio
async def test_runtime_01c_technical_failure_skill_raises_not_partial(
    db_session,
    biv_runtime_env,
) -> None:
    from app.business_idea_validation.pipeline_metrics import BivPipelineMetricsRecorder
    from app.business_idea_validation.pipeline_validator import PipelineValidationResult
    from app.schemas.contracts import BivPipelineFailure

    skill = BusinessIdeaValidationSkill(db_session, get_settings())
    gate = PipelineValidationResult(
        passed=False,
        failure=BivPipelineFailure(
            failure_stage="fetch",
            failure_code="pipeline_fetch_failed",
            retryable=True,
            safe_message="Fetch failed",
        ),
        blockers=[],
    )
    ctx = PartialResearchBuildContext(
        investigation_id=uuid4(),
        partial_report=BivPartialResearchReport(established_findings=["x"]),
        evidence_items=[_accepted_evidence()],
        finding_items=[],
        sources=[],
        evidence=[],
        findings=[],
        risks=[],
        opportunities=[],
        research_plan=[],
        coverage_plan=ResearchCoveragePlan(),
        research_gaps=[],
        research_gap_items=[],
        semantic_gap_groups=[],
        remediation_questions=[],
        category_coverage=[],
        research_stop_reason=None,
        confidence=BusinessIdeaValidationConfidence(total_score=10),
        limitations=[],
        mcp_search_calls=1,
        mcp_fetch_calls=0,
        research_rounds_completed=1,
    )
    recorder = BivPipelineMetricsRecorder()
    recorder.record_queries_generated(1)
    recorder.data.discovery.search_success_count = 1
    partial = await skill._try_partial_research_delivery(
        gate,
        build_ctx=ctx,
        observability=None,
        pipeline_metrics=recorder,
        run_id=None,
    )
    assert partial is None
