"""PRODUCT-01.3B.2A — research execution quality tests."""

from __future__ import annotations

from uuid import uuid4

from app.business_idea_validation.commercial_relevance import assess_commercial_relevance
from app.business_idea_validation.coverage_contract import build_partial_report
from app.business_idea_validation.findings import build_findings
from app.business_idea_validation.gap_queries import build_gap_queries
from app.business_idea_validation.research_decomposition import decompose_intake
from app.business_idea_validation.research_plan import build_research_plan
from app.db.base import utc_now
from app.schemas.contracts import (
    BivEvidenceClassification,
    BusinessIdeaValidationEvidenceSummary,
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
        known_competitors="неизвестно",
        current_stage="разработка",
        analysis_goal="проверить жизнеспособность идеи",
        product_or_service="SaaS",
    )
    defaults.update(kwargs)
    return BusinessIdeaValidationInput(**defaults)


def _evidence(**kwargs) -> BusinessIdeaValidationEvidenceSummary:
    defaults = dict(
        evidence_id=uuid4(),
        source_id=uuid4(),
        category="market",
        classification=BivEvidenceClassification.CONFIRMED,
        claim="Default claim with enough length for validation.",
        observation="Default observation with enough length.",
        supporting_excerpt="excerpt",
        source_url="https://example.com/a",
        source_title="Example",
        retrieved_at=utc_now(),
        relevance_score=0.8,
        reliability_score=0.8,
        freshness_score=0.7,
        sanitized=True,
        mcp_server_role="web_fetch_mcp",
        mcp_tool_name="fetch",
    )
    defaults.update(kwargs)
    return BusinessIdeaValidationEvidenceSummary(**defaults)


def test_decompose_extracts_use_case_not_bare_saas() -> None:
    decomp = decompose_intake(_saas_inp())
    assert "маркетинг" in decomp.use_case.lower()
    assert "ai" in decomp.core_search_subject.lower() or "маркетинг" in decomp.core_search_subject.lower()
    assert "alternatives" in decomp.clarification_needed


def test_queries_exclude_unknown_and_duplicate_saas() -> None:
    plan = build_research_plan(_saas_inp())
    for item in plan:
        q = item.query.lower()
        assert "неизвестно" not in q
        assert "unknown" not in q
        assert "saas saas" not in q


def test_queries_include_commercial_use_case_terms() -> None:
    plan = build_research_plan(_saas_inp())
    joined = " ".join(item.query.lower() for item in plan)
    assert any(term in joined for term in ("ai", "маркетинг", "marketing", "automation", "martech"))


def test_market_and_competitor_queries_are_targeted() -> None:
    plan = build_research_plan(_saas_inp())
    market_queries = [i.query.lower() for i in plan if i.category == "market"]
    competitor_queries = [i.query.lower() for i in plan if i.category == "competitors"]
    assert market_queries
    assert competitor_queries
    assert any("ai" in q or "martech" in q for q in market_queries)
    assert all("неизвестно" not in q for q in competitor_queries)


def test_gap_queries_also_exclude_unknown() -> None:
    gaps = build_gap_queries(_saas_inp(), ["market", "competitors"])
    for item in gaps:
        assert "неизвестно" not in item.query.lower()


def test_commercial_relevance_rejects_generic_blogger_economy() -> None:
    inp = _saas_inp()
    result = assess_commercial_relevance(
        inp=inp,
        category="market",
        observation="Блогеры — значимый сегмент российской экономики.",
    )
    assert not result.relevant


def test_commercial_relevance_rejects_youtube_brand_stat_for_demand() -> None:
    inp = _saas_inp()
    result = assess_commercial_relevance(
        inp=inp,
        category="demand",
        observation="38% брендов используют YouTube-блогеров для продвижения.",
    )
    assert not result.relevant


def test_commercial_relevance_accepts_marketing_automation_signal() -> None:
    inp = _saas_inp()
    result = assess_commercial_relevance(
        inp=inp,
        category="market",
        observation=(
            "Рынок marketing automation SaaS в России растёт; компании инвестируют "
            "в AI-инструменты для контент-маркетинга."
        ),
    )
    assert result.relevant


def test_commercial_relevance_accepts_audience_pain() -> None:
    inp = _saas_inp()
    result = assess_commercial_relevance(
        inp=inp,
        category="audience",
        observation=(
            "Маркетологи малых команд тратят много времени на рутинный контент "
            "и ищут AI-автоматизацию."
        ),
    )
    assert result.relevant


def test_build_findings_filters_non_commercial_confirmed_evidence() -> None:
    inp = _saas_inp()
    evidence = [
        _evidence(
            category="market",
            claim="Блогеры — сегмент российской экономики.",
            observation="Блогеры — сегмент российской экономики.",
        ),
        _evidence(
            category="competitors",
            claim="HubSpot и Jasper предлагают AI-маркетинговые инструменты для команд.",
            observation="HubSpot и Jasper предлагают AI-маркетинговые инструменты для команд.",
        ),
    ]
    findings = build_findings(evidence, inp=inp)
    categories = {f.category for f in findings}
    assert "market" not in categories
    assert "competitors" in categories


def test_partial_report_no_unsupported_promising_conclusion() -> None:
    report = build_partial_report(
        inp=_saas_inp(),
        findings=[],
        evidence=[],
        gate_passed=False,
        category_coverage=[],
    )
    assert "перспектив" not in report.interim_conclusion.lower()
    assert "гипотез" not in report.interim_conclusion.lower() or "недостаточно" in report.interim_conclusion.lower()


def test_partial_report_filters_generic_probable_signals() -> None:
    inp = _saas_inp()
    evidence = [
        _evidence(
            category="demand",
            classification=BivEvidenceClassification.HYPOTHESIS,
            claim="38% брендов работают с YouTube-блогерами.",
            observation="38% брендов работают с YouTube-блогерами.",
            relevance_score=0.5,
            reliability_score=0.5,
            freshness_score=0.5,
        ),
    ]
    report = build_partial_report(
        inp=inp,
        findings=[],
        evidence=evidence,
        gate_passed=False,
        category_coverage=[],
    )
    assert not report.probable_signals


def test_research_plan_has_two_queries_per_core_category() -> None:
    plan = build_research_plan(_saas_inp())
    market_queries = [i for i in plan if i.category == "market"]
    assert len(market_queries) >= 2
