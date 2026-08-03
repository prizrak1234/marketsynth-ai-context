"""Integration tests for fetch orchestrator fallback contour."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.business_idea_validation.fetch_orchestrator import BivFetchOrchestrator
from app.business_idea_validation.pipeline_metrics import BivPipelineMetricsRecorder
from app.business_idea_validation.research_fetch.port import FetchRequest, FetchResult, ResearchFetchStatus
from app.business_tools.contracts import BusinessToolError
from app.core.config import get_settings
from app.db.base import utc_now
from app.schemas.contracts import BivFetchOutcomeCode
import hashlib


def _success_result(request: FetchRequest, body: str, title: str = "Example title") -> FetchResult:
    text = body.strip()
    return FetchResult(
        provider="trafilatura",
        source_url=request.source_url,
        final_url=request.normalized_url,
        normalized_url=request.normalized_url,
        fetched_at=utc_now(),
        status=ResearchFetchStatus.SUCCEEDED,
        http_status=200,
        content_type="text/html",
        title=title,
        raw_html=None,
        extracted_text=text,
        markdown=None,
        language=None,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        byte_count=len(text.encode()),
        latency_ms=10,
        attempt_number=1,
    )


@pytest.mark.asyncio
async def test_primary_429_then_direct_http_success(monkeypatch) -> None:
    """Checkpoint 2 — primary rate limit, secondary trafilatura success, both in ledger."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    appended: list = []

    async def _capture_append(self, row):
        appended.append(row)
        row.id = uuid4()
        return row

    from app.db.repositories import biv_fetch_ledger as ledger_mod

    monkeypatch.setattr(ledger_mod.BivFetchLedgerRepository, "append", _capture_append)

    settings = get_settings()
    settings.research_fetch_provider_order = "firecrawl,trafilatura"
    metrics = BivPipelineMetricsRecorder()
    run_id = uuid4()
    orchestrator = BivFetchOrchestrator(
        session,
        settings,
        run_id=run_id,
        correlation_id="corr-fallback",
        metrics=metrics,
    )

    async def _mcp_fetch(*, url: str):
        raise BusinessToolError(category="rate_limited", message="429")

    body = (
        "Enterprise demand for AI marketing tools continues to grow among mid-market SaaS "
        "companies with measurable retention outcomes and repeatable onboarding playbooks."
    )

    async def _traf_fetch(self, request: FetchRequest):
        return _success_result(request, body)

    monkeypatch.setattr(
        "app.business_idea_validation.research_fetch.providers.trafilatura.LocalTrafilaturaFetchAdapter.fetch",
        _traf_fetch,
    )

    result = await orchestrator.fetch_url(
        "https://example.com/market-report",
        query_id="q-test",
        mcp_fetch=_mcp_fetch,
    )

    assert result.success is True
    assert result.fallback_used is True
    assert result.outcome == BivFetchOutcomeCode.SUCCESS
    assert len(appended) >= 1
    assert any(row.provider == "trafilatura" for row in appended)
    assert metrics.data.fetch.fallback_success_count == 1


@pytest.mark.asyncio
async def test_credits_exhausted_still_falls_back_to_direct_http(monkeypatch) -> None:
    """Non-retryable Firecrawl credits_exhausted must not skip trafilatura fallback."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    appended: list = []

    async def _capture_append(self, row):
        appended.append(row)
        row.id = uuid4()
        return row

    from app.db.repositories import biv_fetch_ledger as ledger_mod

    monkeypatch.setattr(ledger_mod.BivFetchLedgerRepository, "append", _capture_append)

    settings = get_settings()
    settings.research_fetch_provider_order = "firecrawl,trafilatura"
    orchestrator = BivFetchOrchestrator(
        session,
        settings,
        run_id=uuid4(),
        correlation_id="corr-credits",
        metrics=BivPipelineMetricsRecorder(),
    )

    async def _mcp_fetch(*, url: str):
        raise BusinessToolError(category="credits_exhausted", message="402")

    body = (
        "Russian SaaS marketing automation market shows growing demand for AI-assisted "
        "campaign planning among small and medium businesses with subscription pricing."
    )

    async def _traf_fetch(self, request: FetchRequest):
        return _success_result(request, body, title="Market title")

    monkeypatch.setattr(
        "app.business_idea_validation.research_fetch.providers.trafilatura.LocalTrafilaturaFetchAdapter.fetch",
        _traf_fetch,
    )

    result = await orchestrator.fetch_url(
        "https://example.com/saas-market",
        query_id="q-credits",
        mcp_fetch=_mcp_fetch,
    )

    assert result.success is True
    assert result.fallback_used is True
    assert any(row.provider == "trafilatura" and row.outcome_code == "success" for row in appended)
