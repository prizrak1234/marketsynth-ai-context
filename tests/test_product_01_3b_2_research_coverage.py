"""PRODUCT-01.3B.2 — research coverage contract tests."""

from __future__ import annotations

from uuid import uuid4

from app.business_idea_validation.coverage_contract import (
    CategoryAttemptStats,
    CoverageAttemptTracker,
    build_category_coverage,
    build_intake_hypotheses,
    build_partial_report,
    build_remediation_questions,
    build_research_stop_reason,
    dedupe_research_gaps,
    derive_coverage_status,
)
from app.business_idea_validation.coverage_gate import CoverageGateResult, evaluate_coverage_gate
from app.business_idea_validation.research_plan import build_research_plan
from app.schemas.contracts import (
    BivCoverageAttemptStatus,
    BusinessIdeaValidationInput,
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
        pricing_or_revenue_model="200–900 долларов в месяц",
        current_stage="разработка",
        analysis_goal="проверить жизнеспособность идеи",
        product_or_service="SaaS",
    )
    defaults.update(kwargs)
    return BusinessIdeaValidationInput(**defaults)


def test_research_plan_has_all_canonical_categories_for_rf() -> None:
    plan = build_research_plan(_saas_inp())
    categories = {item.category for item in plan}
    assert "market" in categories
    assert "competitors" in categories
    assert "audience" in categories
    assert "demand" in categories
    assert "pricing" in categories
    assert "commercial_risks" in categories
    assert "local_context" in categories
    assert all(item.query for item in plan)
    joined = " ".join(item.query.lower() for item in plan)
    assert "неизвестно" not in joined
    assert "saas saas" not in joined
    assert any(
        term in joined
        for term in ("ai", "маркетинг", "marketing", "automation", "martech")
    )


def test_intake_hypotheses_mark_pricing_and_audience() -> None:
    hypotheses = build_intake_hypotheses(_saas_inp())
    fields = {h.field for h in hypotheses}
    assert "pricing_or_revenue_model" in fields
    assert "target_customer" in fields
    pricing_hyp = next(h for h in hypotheses if h.field == "pricing_or_revenue_model")
    assert "пользовател" in pricing_hyp.message.lower()


def test_coverage_status_distinctions() -> None:
    not_researched = derive_coverage_status(CategoryAttemptStats(category="market", searched=False))
    assert not_researched == BivCoverageAttemptStatus.NOT_RESEARCHED

    not_found = derive_coverage_status(
        CategoryAttemptStats(category="market", searched=True, sources_found=0),
    )
    assert not_found == BivCoverageAttemptStatus.NOT_FOUND

    confirmed = derive_coverage_status(
        CategoryAttemptStats(
            category="market",
            searched=True,
            sources_relevant=1,
            evidence_confirmed=1,
        ),
    )
    assert confirmed == BivCoverageAttemptStatus.CONFIRMED

    hypothesis_only = derive_coverage_status(
        CategoryAttemptStats(
            category="audience",
            searched=True,
            sources_relevant=1,
            evidence_hypothesis=1,
        ),
    )
    assert hypothesis_only == BivCoverageAttemptStatus.NOT_CONFIRMED


def test_category_coverage_marks_user_hypothesis_for_pricing() -> None:
    tracker = CoverageAttemptTracker()
    tracker.record_query("pricing", "цены SaaS маркетинг")
    tracker.record_query("market", "рынок SaaS РФ")
    plan = build_research_plan(_saas_inp())
    summaries = build_category_coverage(inp=_saas_inp(), tracker=tracker, plan_items=plan)
    pricing = next(s for s in summaries if s.category == "pricing")
    assert pricing.coverage_status == BivCoverageAttemptStatus.USER_HYPOTHESIS
    assert pricing.executed_query


def test_dedupe_research_gaps_drops_redundant_coverage_codes() -> None:
    codes = dedupe_research_gaps(
        [
            "fewer_than_3_fetched_sources",
            "coverage_market_insufficient",
            "coverage_competitors_insufficient",
            "missing_market_finding",
        ],
    )
    assert "coverage_market_insufficient" not in codes
    assert "fewer_than_3_fetched_sources" in codes
    assert "missing_market_finding" in codes


def test_remediation_questions_are_specific_not_generic() -> None:
    tracker = CoverageAttemptTracker()
    for cat in ("market", "competitors", "audience", "demand", "pricing"):
        tracker.record_query(cat, f"query {cat}")
    plan = build_research_plan(_saas_inp())
    coverage = build_category_coverage(inp=_saas_inp(), tracker=tracker, plan_items=plan)
    questions = build_remediation_questions(coverage)
    assert len(questions) >= 3
    assert all("?" in q.question for q in questions)
    assert not any(q.question.lower() == "уточните контекст." for q in questions)


def test_partial_report_includes_interim_conclusion_when_empty() -> None:
    gate = CoverageGateResult(passed=False, limitations=["fewer_than_3_fetched_sources"])
    tracker = CoverageAttemptTracker()
    plan = build_research_plan(_saas_inp())
    coverage = build_category_coverage(inp=_saas_inp(), tracker=tracker, plan_items=plan)
    report = build_partial_report(
        inp=_saas_inp(),
        findings=[],
        evidence=[],
        gate_passed=False,
        category_coverage=coverage,
    )
    assert report.interim_conclusion
    assert report.user_hypotheses
    assert any("200" in h.value for h in report.user_hypotheses)


def test_stop_reason_is_customer_safe() -> None:
    inp = _saas_inp(target_audience=None)
    gate = CoverageGateResult(passed=False, limitations=["missing_audience_finding"])
    stop = build_research_stop_reason(
        inp=inp,
        gate_passed=False,
        limitations=["missing_audience_finding"],
        sources=[],
        category_coverage=[],
        mcp_search_calls=0,
    )
    assert stop.customer_message
    assert "ICP" in stop.customer_message or "платящ" in stop.customer_message.lower()


def test_evaluate_coverage_gate_requires_demand_and_competitors() -> None:
    inp = _saas_inp()
    gate = evaluate_coverage_gate(
        inp=inp,
        sources=[],
        evidence=[],
        findings=[],
        risks=[],
        audience=None,
        coverage_plan=None,
    )
    assert not gate.passed
    assert "missing_market_finding" in gate.limitations
    assert "missing_competitor_finding" in gate.limitations
    assert "missing_demand_finding" in gate.limitations
