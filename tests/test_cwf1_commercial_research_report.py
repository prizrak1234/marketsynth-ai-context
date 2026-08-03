"""CWF.1 — customer report and cascade pipeline tests."""

from __future__ import annotations

from uuid import uuid4

from app.business_idea_validation.confidence import calculate_confidence
from app.business_idea_validation.coverage_contract import (
    CategoryAttemptStats,
    CoverageAttemptTracker,
    build_category_coverage,
    derive_coverage_status,
)
from app.business_idea_validation.customer_report import build_customer_research_report
from app.business_idea_validation.research_cascade import (
    PIPELINE_PHASES,
    build_cascade_research_plan,
)
from app.schemas.contracts import (
    BivCoverageAttemptStatus,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationVerdictKind,
)


def _saas_inp(**kwargs) -> BusinessIdeaValidationInput:
    defaults = dict(
        tenant_id=uuid4(),
        project_id=uuid4(),
        user_request_id=uuid4(),
        idea="AI-маркетинговое агентство полного цикла для маркетологов и блогеров",
        market="SaaS",
        location="РФ",
        target_audience="маркетологи, блогеры",
        pricing_or_revenue_model="200–900 USD/month",
        known_competitors="неизвестно",
    )
    defaults.update(kwargs)
    return BusinessIdeaValidationInput(**defaults)


def test_cascade_plan_includes_all_pipeline_phases() -> None:
    plan = build_cascade_research_plan(_saas_inp())
    phases = {item.pipeline_phase for item in plan}
    assert "direct" in phases
    assert "international" in phases
    assert "local" in phases
    assert len(plan) > len(PIPELINE_PHASES)


def test_customer_report_has_no_forbidden_engine_labels() -> None:
    inp = _saas_inp()
    tracker = CoverageAttemptTracker()
    for cat in ("market", "competitors", "demand"):
        tracker.record_query(cat, f"internal query {cat}")
        tracker.record_fetch(cat, relevant=False, low_quality=False)
    plan = build_cascade_research_plan(inp)[:3]
    coverage = build_category_coverage(inp=inp, tracker=tracker, plan_items=plan)
    confidence = calculate_confidence(
        sources=[],
        evidence=[],
        contradiction_count=0,
        unresolved_assumption_count=2,
        gate_passed=False,
    )
    report = build_customer_research_report(
        inp=inp,
        findings=[],
        evidence=[],
        risks=[],
        category_coverage=coverage,
        plan_items=plan,
        confidence=confidence,
        gate_passed=False,
        verdict=BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        phases_executed=["direct", "international"],
    )
    blob = report.executive_summary.status_line.lower()
    assert "неизвестно" not in blob
    assert "недостаточно данных" not in blob
    assert report.clarification_questions
    assert report.overall_confidence_percent == confidence.total_score


def test_unconfirmed_topics_use_professional_framing() -> None:
    stats = CategoryAttemptStats(category="market", searched=True, sources_found=0)
    status = derive_coverage_status(stats)
    assert status == BivCoverageAttemptStatus.NOT_FOUND

    inp = _saas_inp()
    tracker = CoverageAttemptTracker()
    tracker.record_query("market", "q")
    coverage = build_category_coverage(
        inp=inp,
        tracker=tracker,
        plan_items=build_cascade_research_plan(inp)[:1],
    )
    report = build_customer_research_report(
        inp=inp,
        findings=[],
        evidence=[],
        risks=[],
        category_coverage=coverage,
        plan_items=build_cascade_research_plan(inp)[:2],
        confidence=calculate_confidence(
            sources=[],
            evidence=[],
            contradiction_count=0,
            unresolved_assumption_count=1,
            gate_passed=False,
        ),
        gate_passed=False,
        verdict=BusinessIdeaValidationVerdictKind.REVISE,
        phases_executed=["direct"],
    )
    if report.unconfirmed_topics:
        topic = report.unconfirmed_topics[0]
        assert "Не удалось подтвердить" not in topic.topic
        assert topic.reason
        assert topic.methods_used
