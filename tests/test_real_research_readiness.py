"""REAL-RESEARCH-READINESS — automated validation gates and provider smoke."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.business_idea_validation.real_research_readiness import (
    provider_smoke_passed,
    validate_evidence_integrity,
    validate_export,
    validate_minimum_real_research,
    validate_query_decomposition,
    validate_run_output,
)
from app.business_tools.contracts import BusinessToolError, SourceCandidate, WebSearchResult
from app.business_tools.providers.firecrawl_fetch import FirecrawlFetchTool
from app.business_tools.providers.xmlriver_search import XmlRiverSearchTool
from app.core.config import get_settings
from app.schemas.contracts import (
    BivCommercialVerdict,
    BivCommercialVerdictKind,
    BivCustomerResearchReport,
    BivEvidenceItem,
    BivFindingItem,
    BivRunObservability,
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationResearchPlanItem,
    BusinessIdeaValidationVerdictKind,
)


def _sample_output() -> BusinessIdeaValidationOutput:
    eid = uuid4()
    return BusinessIdeaValidationOutput(
        investigation_id=uuid4(),
        verdict=BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS,
        confidence=BusinessIdeaValidationConfidence(total_score=62),
        research_plan=[
            BusinessIdeaValidationResearchPlanItem(
                category="market",
                query="рынок AI marketing software Россия",
                rationale="market size",
                pipeline_phase="initial",
            ),
            BusinessIdeaValidationResearchPlanItem(
                category="competitors",
                query="конкуренты marketing automation SaaS Россия",
                rationale="competition",
                pipeline_phase="initial",
            ),
            BusinessIdeaValidationResearchPlanItem(
                category="demand",
                query="спрос AI маркетинг маркетологи Россия",
                rationale="demand",
                pipeline_phase="initial",
            ),
            BusinessIdeaValidationResearchPlanItem(
                category="pricing",
                query="цены подписка marketing SaaS 200 900 долларов",
                rationale="pricing",
                pipeline_phase="initial",
            ),
        ],
        evidence_items=[
            BivEvidenceItem(
                evidence_id=eid,
                source_url="https://example.com/report",
                source_title="Example market report",
                accessed_at=datetime.now(UTC),
                excerpt="Demand for marketing automation continues to grow among SMB teams.",
                claim_supported="Marketing automation demand signal for SMB.",
                relevance_score=0.8,
                quality_score=0.7,
                freshness_score=0.6,
                accepted=True,
            )
        ],
        finding_items=[
            BivFindingItem(
                finding_id=uuid4(),
                category="market",
                claim="Marketing automation demand exists among SMB teams.",
                interpretation="Local relevance likely but needs pricing proof.",
                business_impact="Supports pilot positioning.",
                evidence_ids=[eid],
                confidence=0.7,
            )
        ],
        commercial_verdict=BivCommercialVerdict(
            kind=BivCommercialVerdictKind.CONDITIONAL_GO,
            rationale=(
                "Demand signals exist for marketing automation, but local pricing "
                "and competitor proof remain partial — pilot only before scale."
            ),
            confidence=62,
            next_validation_action="Run 10 SMB marketer interviews to validate WTP.",
        ),
        customer_report=BivCustomerResearchReport(
            executive_summary={
                "status_line": "CONDITIONAL GO — pilot with constraints",
                "confidence_percent": 62,
                "primary_advantage": "Automation demand signal",
                "primary_risk": "Pricing not confirmed",
            },
            overall_confidence_percent=62,
            coverage={"overall_percent": 55, "dimensions_researched": ["market", "demand"]},
            structured_verdict={
                "recommendation": "Pilot with 5 paying design partners before full launch.",
                "confidence_percent": 62,
                "confirmed_summary": ["SMB automation demand referenced in sources"],
                "unconfirmed_summary": ["Local pricing benchmarks"],
                "risks": ["Competitive density unclear"],
                "verification_needed": ["WTP interviews"],
            },
        ),
    )


def test_query_decomposition_requires_multiple_distinct_queries() -> None:
    output = _sample_output()
    assert not validate_query_decomposition(output)
    bad = output.model_copy(
        update={
            "research_plan": [
                BusinessIdeaValidationResearchPlanItem(
                    category="market",
                    query="один длинный запрос " * 20,
                    rationale="x",
                    pipeline_phase="initial",
                )
            ]
        }
    )
    assert validate_query_decomposition(bad)


def test_evidence_integrity_blocks_rejected_and_empty_urls() -> None:
    output = _sample_output()
    assert not validate_evidence_integrity(output)
    eid = output.evidence_items[0].evidence_id
    broken = output.model_copy(
        update={
            "evidence_items": [
                output.evidence_items[0].model_copy(update={"source_url": "", "accepted": True})
            ],
            "finding_items": [
                output.finding_items[0].model_copy(update={"evidence_ids": [eid]})
            ],
        }
    )
    assert any("empty_evidence_url" in v for v in validate_evidence_integrity(broken))


def test_validate_run_output_passes_sample() -> None:
    settings = get_settings()
    result = validate_run_output(_sample_output(), settings=settings)
    assert result.metrics["findings"] == 1
    assert result.metrics["accepted_sources"] == 1
    # Minimum real-research gate requires >=3 accepted sources
    assert any("fewer_than_3_accepted_sources" in b for b in result.blockers)


def test_provider_smoke_passed_ready() -> None:
    ok, blocker = provider_smoke_passed(
        {
            "status": "ready",
            "mock_providers": False,
            "providers": {
                "xmlriver": {"state": "ready"},
                "firecrawl": {"state": "ready"},
            },
        }
    )
    assert ok is True
    assert blocker is None


def test_provider_smoke_fails_on_mock() -> None:
    ok, blocker = provider_smoke_passed({"mock_providers": True, "status": "ready"})
    assert ok is False
    assert blocker == "mock_providers_enabled"


@pytest.mark.asyncio
async def test_xmlriver_probe_maps_invalid_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResp:
        status_code = 403
        text = ""

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResp()

    monkeypatch.setenv("XMLRIVER_USER_ID", "u")
    monkeypatch.setenv("XMLRIVER_API_KEY", "k")
    get_settings.cache_clear()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeClient())
    with pytest.raises(BusinessToolError) as exc:
        await XmlRiverSearchTool().search("test")
    assert exc.value.category == "invalid_credentials"


@pytest.mark.asyncio
async def test_xmlriver_probe_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(self, query: str, *, limit: int = 5) -> WebSearchResult:
        return WebSearchResult(
            query=query,
            provider="xmlriver",
            candidates=[SourceCandidate(url="https://example.com", provider="xmlriver")],
        )

    monkeypatch.setattr(XmlRiverSearchTool, "search", fake_search)
    result = await XmlRiverSearchTool().probe()
    assert result["result_count"] == 1


@pytest.mark.asyncio
async def test_firecrawl_probe_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.business_tools.contracts import SourceFetchResult

    async def fake_fetch(self, url: str) -> SourceFetchResult:
        return SourceFetchResult(
            url=url,
            provider="firecrawl",
            candidate=SourceCandidate(url=url, provider="firecrawl"),
            normalized_text_excerpt="Example Domain body text for probe.",
        )

    monkeypatch.setattr(FirecrawlFetchTool, "fetch", fake_fetch)
    result = await FirecrawlFetchTool().probe()
    assert result["ok"] is True


def test_export_validation_on_sample_output() -> None:
    output = _sample_output()
    violations = validate_export(output)
    assert isinstance(violations, list)


@pytest.mark.real_providers
@pytest.mark.asyncio
async def test_real_provider_probe_integration() -> None:
    import os

    if os.getenv("REAL_PROVIDERS_INTEGRATION") != "1":
        pytest.skip("Set REAL_PROVIDERS_INTEGRATION=1 to run live provider probes")
    from app.research_source_collection.readiness import probe_providers

    get_settings.cache_clear()
    settings = get_settings()
    if settings.research_source_collection_mock_providers:
        pytest.skip("Disable RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS for live probe")
    payload = await probe_providers(settings, live=True)
    ok, blocker = provider_smoke_passed(payload)
    assert ok, blocker


def test_minimum_real_research_blocks_zero_fetch() -> None:
    output = _sample_output().model_copy(update={"mcp_search_calls": 10, "mcp_fetch_calls": 0})
    blockers = validate_minimum_real_research(output)
    assert "search_without_successful_fetch" in blockers


def test_budget_validation_flags_excess_search() -> None:
    settings = get_settings()
    output = _sample_output()
    obs = BivRunObservability(
        correlation_id="c1",
        run_id=uuid4(),
        project_id=uuid4(),
        user_request_id=uuid4(),
        started_at=datetime.now(UTC),
        search_count=settings.biv_research_max_search_calls + 1,
        fetch_count=1,
        total_latency_ms=1000,
    )
    result = validate_run_output(output, observability=obs, settings=settings)
    assert "search_budget_exceeded" in result.blockers
