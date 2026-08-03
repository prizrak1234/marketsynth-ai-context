"""BIV stabilization slice — progress, verdict, contracts, backfill."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.business_idea_validation.commercial_verdict import (
    build_commercial_verdict,
    map_legacy_verdict_kind,
)
from app.business_idea_validation.evidence_contract import build_evidence_items, build_finding_items
from app.business_idea_validation.output_enrichment import enrich_output_commercial
from app.business_idea_validation.progress_persistence import PersistingBivRunProgressTracker
from app.business_idea_validation.run_progress import BivRunProgressTracker
from app.db.base import utc_now
from app.schemas.contracts import (
    BivCommercialVerdictKind,
    BivPipelineStage,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationRunStatus,
    BusinessIdeaValidationVerdictKind,
)
from tests.test_cwf_1a_launch_pack_decision import _output


def test_progress_tracker_stages_monotonic() -> None:
    tracker = BivRunProgressTracker(run_id=uuid4(), correlation_id="corr-1")
    tracker.advance(BivPipelineStage.NORMALIZING_INPUT)
    tracker.advance(BivPipelineStage.SEARCHING_DIRECT)
    snap = tracker.snapshot()
    assert snap.state == BusinessIdeaValidationRunStatus.RUNNING
    assert snap.current_stage == BivPipelineStage.SEARCHING_DIRECT
    assert BivPipelineStage.NORMALIZING_INPUT in snap.completed_stages
    assert 0 < snap.progress_percent < 100


def test_progress_completed_is_100_percent() -> None:
    tracker = BivRunProgressTracker(run_id=uuid4(), correlation_id="corr-2")
    tracker.advance(BivPipelineStage.COMPLETED)
    snap = tracker.snapshot()
    assert snap.progress_percent == 100
    assert snap.state == BusinessIdeaValidationRunStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_persisting_progress_tracker_calls_hook() -> None:
    calls: list[int] = []

    async def persist(_snap) -> None:
        calls.append(1)

    tracker = PersistingBivRunProgressTracker(
        run_id=uuid4(),
        correlation_id="corr-3",
        on_persist=persist,
    )
    tracker.advance(BivPipelineStage.DECOMPOSING_QUERIES)
    await __import__("asyncio").sleep(0.05)
    assert len(calls) >= 1


def test_verdict_mapping_covers_all_kinds() -> None:
    assert map_legacy_verdict_kind(
        BusinessIdeaValidationVerdictKind.REJECT,
        gate_passed=False,
        confidence=20,
        confirmed_count=0,
    ) == BivCommercialVerdictKind.NO_GO
    assert map_legacy_verdict_kind(
        BusinessIdeaValidationVerdictKind.PROCEED,
        gate_passed=True,
        confidence=80,
        confirmed_count=5,
    ) == BivCommercialVerdictKind.GO
    pilot = map_legacy_verdict_kind(
        BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        gate_passed=False,
        confidence=40,
        confirmed_count=1,
    )
    assert pilot == BivCommercialVerdictKind.PILOT_ONLY


def test_commercial_verdict_has_required_fields() -> None:
    verdict = build_commercial_verdict(
        kind=BivCommercialVerdictKind.HOLD,
        confidence=25,
        findings=[],
        risks=[],
        unconfirmed_topics=["ICP не подтверждён"],
        gate_passed=False,
    )
    assert verdict.rationale
    assert verdict.next_validation_action
    assert verdict.go_no_go_conditions


def test_finding_requires_accepted_evidence() -> None:
    eid = uuid4()
    evidence = BusinessIdeaValidationEvidenceSummary(
        evidence_id=eid,
        source_id=uuid4(),
        category="market",
        claim="Confirmed market signal with sufficient length.",
        supporting_excerpt="Market grows 12% annually in target region.",
        source_url="https://example.com/market-report",
        source_title="Market Report",
        retrieved_at=utc_now(),
        relevance_score=0.8,
        reliability_score=0.7,
        freshness_score=0.7,
        mcp_server_role="web_fetch_mcp",
        mcp_tool_name="fetch",
    )
    items = build_evidence_items([evidence])
    findings = build_finding_items(
        [
            BusinessIdeaValidationFinding(
                category="market",
                title="Market",
                statement="Demand exists for the offer.",
                linked_evidence_ids=[eid],
            )
        ],
        items,
    )
    assert len(findings) == 1
    rejected = build_evidence_items(
        [
            evidence.model_copy(
                update={
                    "observation": "[Смотреть рейтинг]()",
                    "claim": "[Смотреть рейтинг]()",
                    "supporting_excerpt": "[Смотреть рейтинг]()",
                }
            )
        ]
    )
    assert all(not e.accepted for e in rejected)
    assert (
        build_finding_items(
            [
                BusinessIdeaValidationFinding(
                    category="market",
                    title="Market",
                    statement="Should not appear.",
                    linked_evidence_ids=[eid],
                )
            ],
            rejected,
        )
        == []
    )


def test_enrich_output_backfills_commercial_contract() -> None:
    base = _output(BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS)
    enriched = enrich_output_commercial(base)
    assert enriched.customer_report is not None
    assert enriched.commercial_verdict is not None
    assert enriched.commercial_verdict.kind in BivCommercialVerdictKind
