"""CMVP.1.1 — gap-directed coverage, source quality, backend hydration."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.business_idea_validation.audience_segmentation import (
    audience_has_support,
    run_audience_segmentation,
)
from app.business_idea_validation.confidence import CALCULATION_VERSION, calculate_confidence
from app.business_idea_validation.coverage_gate import (
    evaluate_coverage_gate,
    positive_verdict_allowed,
)
from app.business_idea_validation.coverage_plan import (
    build_initial_coverage_plan,
    missing_categories_for_retry,
    update_coverage_plan,
)
from app.business_idea_validation.gap_queries import build_gap_queries
from app.business_idea_validation.source_quality import classify_source, publisher_root
from app.schemas.contracts import (
    AudienceSegmentationOutput,
    BusinessIdeaValidationEvidenceSummary,
    BusinessIdeaValidationFinding,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationRisk,
    BusinessIdeaValidationSourceSummary,
    BusinessIdeaValidationVerdictKind,
    ResearchCoverageCategoryStatus,
    SourceStatus,
    SourceType,
)
from app.db.base import utc_now
from fastapi.testclient import TestClient


def _inp(**kwargs) -> BusinessIdeaValidationInput:
    return BusinessIdeaValidationInput(
        tenant_id=uuid4(),
        project_id=uuid4(),
        user_request_id=uuid4(),
        idea="Open a take-away coffee shop downtown",
        **kwargs,
    )


def _source(**kwargs) -> BusinessIdeaValidationSourceSummary:
    defaults = dict(
        source_id=uuid4(),
        url="https://example.com/a",
        title="Example",
        domain="example.com",
        retrieved_at=utc_now(),
        source_type=SourceType.WEBSITE,
        status=SourceStatus.AVAILABLE,
        mcp_server_role="web_fetch_mcp",
        mcp_tool_name="fetch",
        independence_group="example.com",
        research_category="market",
    )
    defaults.update(kwargs)
    return BusinessIdeaValidationSourceSummary(**defaults)


def _evidence(category: str, **kwargs) -> BusinessIdeaValidationEvidenceSummary:
    sid = kwargs.pop("source_id", uuid4())
    defaults = dict(
        evidence_id=uuid4(),
        source_id=sid,
        category=category,
        claim=f"Evidence claim for {category} with enough length.",
        supporting_excerpt="excerpt",
        source_url="https://example.com/a",
        source_title="Example",
        retrieved_at=utc_now(),
        relevance_score=0.8,
        reliability_score=0.7,
        freshness_score=0.7,
        mcp_server_role="web_fetch_mcp",
        mcp_tool_name="fetch",
    )
    defaults.update(kwargs)
    return BusinessIdeaValidationEvidenceSummary(**defaults)


def test_coverage_plan_includes_local_context_when_location_present() -> None:
    plan = build_initial_coverage_plan(_inp(location="Moscow center"))
    categories = {c.category for c in plan.categories}
    assert "local_context" in categories


def test_coverage_plan_excludes_local_context_for_online_b2b() -> None:
    plan = build_initial_coverage_plan(_inp(location=None, market="Global SaaS"))
    categories = {c.category for c in plan.categories}
    assert "local_context" not in categories


def test_missing_category_detection() -> None:
    plan = build_initial_coverage_plan(_inp())
    plan = update_coverage_plan(
        plan,
        sources=[_source(research_category="market")],
        evidence=[_evidence("market")],
        findings=[
            BusinessIdeaValidationFinding(
                category="market",
                title="Market",
                statement="Demand exists.",
                linked_evidence_ids=[],
            )
        ],
        risks=[],
        audience=AudienceSegmentationOutput(),
        searched_categories={"market"},
    )
    missing = missing_categories_for_retry(plan)
    assert "competitors" in missing
    assert "audience" in missing


def test_gap_queries_are_category_specific() -> None:
    queries = build_gap_queries(_inp(location="Moscow"), ["audience", "competitors"])
    assert len(queries) == 2
    assert queries[0].category == "audience"
    assert queries[0].gap_directed is True
    assert len(queries[0].query) > 20


def test_publisher_independence_deduplication() -> None:
    a = classify_source(
        url="https://news.example.com/a",
        domain="news.example.com",
        title="A",
        body_excerpt="market demand growth",
    )
    b = classify_source(
        url="https://blog.example.com/b",
        domain="blog.example.com",
        title="B",
        body_excerpt="competition pricing",
    )
    assert a.independence_group == b.independence_group == publisher_root("news.example.com")


def test_audience_hypothesis_vs_finding() -> None:
    audience = run_audience_segmentation(_inp(target_audience="Office workers"), [])
    assert audience.segments
    assert audience.segments[0].is_hypothesis is True
    assert audience_has_support(audience, []) is False

    ev = _evidence("audience")
    audience2 = run_audience_segmentation(_inp(), [ev])
    assert audience2.segments[0].is_hypothesis is False
    assert audience_has_support(audience2, [ev]) is True


def test_confidence_is_deterministic_cmvp1_1() -> None:
    sources = [_source(domain=f"example{i}.com", independence_group=f"example{i}.com") for i in range(3)]
    evidence = [_evidence(["market", "competitors", "audience"][i]) for i in range(3)]
    a = calculate_confidence(
        sources=sources,
        evidence=evidence,
        contradiction_count=0,
        unresolved_assumption_count=0,
        gate_passed=True,
    )
    b = calculate_confidence(
        sources=sources,
        evidence=evidence,
        contradiction_count=0,
        unresolved_assumption_count=0,
        gate_passed=True,
    )
    assert a.total_score == b.total_score
    assert a.calculation_version == CALCULATION_VERSION == "cmvp1_1_v1"


def test_positive_verdict_requires_reliable_evidence() -> None:
    sources = [_source() for _ in range(3)]
    evidence = [_evidence("market", reliability_score=0.4) for _ in range(3)]
    assert positive_verdict_allowed(gate_passed=True, sources=sources, evidence=evidence) is False


def test_insufficient_gate_for_incomplete_coverage() -> None:
    inp = _inp()
    gate = evaluate_coverage_gate(
        inp=inp,
        sources=[_source()],
        evidence=[_evidence("market")],
        findings=[],
        risks=[],
        audience=AudienceSegmentationOutput(),
    )
    assert gate.passed is False


def test_backend_project_hydration(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
) -> None:
    monkeypatch.setenv("BUSINESS_IDEA_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("MCP_READ_ONLY_ENABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.business_tools.contracts import SourceCandidate, SourceFetchResult, WebSearchResult

    async def fake_search(_self, query: str, *, limit: int = 5) -> WebSearchResult:
        return WebSearchResult(
            query=query,
            provider="xmlriver",
            candidates=[
                SourceCandidate(
                    url=f"https://example{hash(query) % 5}.org/report",
                    title="Report",
                    provider="xmlriver",
                )
            ],
        )

    async def fake_fetch(_self, url: str) -> SourceFetchResult:
        body = (
            "Market demand for coffee remains strong. Competition includes chains. "
            "Target audience prefers take-away. Commercial risks include rent costs."
        )
        return SourceFetchResult(
            url=url,
            provider="firecrawl",
            candidate=SourceCandidate(url=url, title="Fetched", provider="firecrawl"),
            normalized_text_excerpt=body,
        )

    monkeypatch.setattr(
        "app.mcp.adapters.xmlriver_search.XmlRiverSearchMcpAdapter.search",
        fake_search,
    )
    monkeypatch.setattr(
        "app.mcp.adapters.firecrawl_fetch.FirecrawlFetchMcpAdapter.fetch",
        fake_fetch,
    )

    ur = client.post(
        "/user-requests",
        json={
            "text": "Coffee shop take-away validation",
            "selected_scenario": "idea_validation",
            "source": "home_conversation",
        },
        headers=auth_headers,
    )
    assert ur.status_code == 201
    request_id = ur.json()["id"]

    run = client.post(
        f"/user-requests/{request_id}/business-idea-validation/run",
        json={"idempotency_key": f"cmvp11-hydration-{uuid4()}"},
        headers=auth_headers,
    )
    assert run.status_code == 200, run.text
    project_id = run.json().get("project_id")
    assert project_id, run.text

    hydration = client.get(
        f"/projects/{project_id}/business-idea-validation/latest",
        headers=auth_headers,
    )
    assert hydration.status_code == 200, hydration.text
    body = hydration.json()
    assert body["user_request_id"] == request_id
    assert body["output"]["coverage_plan"]["categories"]


def test_tenant_isolation_project_hydration(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    import asyncio
    from tests.conftest import _create_user_with_api_key

    listed = client.get("/user-requests?limit=1", headers=auth_headers)
    if listed.status_code != 200 or not listed.json():
        pytest.skip("no user requests")
    project_id = listed.json()[0].get("project_id")
    if not project_id:
        pytest.skip("no project")

    plain_key, _ = asyncio.run(_create_user_with_api_key())
    resp = client.get(
        f"/projects/{project_id}/business-idea-validation/latest",
        headers={"Authorization": f"Bearer {plain_key}"},
    )
    assert resp.status_code in (403, 404)
