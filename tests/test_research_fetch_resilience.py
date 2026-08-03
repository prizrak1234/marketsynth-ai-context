"""Tests for multi-provider research fetch resilience."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.business_idea_validation.fetch_orchestrator import BivFetchOrchestrator
from app.business_idea_validation.pipeline_metrics import BivPipelineMetricsRecorder
from app.business_idea_validation.research_fetch.policy import (
    is_fallback_eligible,
    parse_provider_order,
)
from app.business_idea_validation.research_fetch.port import FetchRequest, FetchResult, ResearchFetchStatus
from app.business_idea_validation.research_fetch.security import validate_fetch_url
from app.business_tools.contracts import BusinessToolError
from app.core.config import get_settings
from app.db.base import utc_now
from app.schemas.contracts import BivFetchOutcomeCode


def _configure_fetch_chain(settings) -> None:
    settings.research_fetch_provider_order = "firecrawl,trafilatura"
    settings.research_fetch_fallback_enabled = True


def _trafilatura_success_result(request: FetchRequest, *, body: str, title: str = "Title") -> FetchResult:
    text = body.strip()
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
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
        content_hash=content_hash,
        byte_count=len(text.encode("utf-8")),
        latency_ms=12,
        attempt_number=1,
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://127.0.0.1/page", False),
        ("http://localhost/admin", False),
        ("http://[::1]/x", False),
        ("http://192.168.1.1/internal", False),
        ("file:///etc/passwd", False),
        ("ftp://example.com/x", False),
        ("https://example.com/article", True),
        ("https://example.com/path...", False),
    ],
)
def test_security_url_validation(url: str, expected: bool) -> None:
    safe, _ = validate_fetch_url(url)
    assert safe is expected


def test_parse_provider_order_default() -> None:
    settings = get_settings()
    order = parse_provider_order(settings)
    assert order[0] == "firecrawl"
    assert "trafilatura" in order
    assert "playwright" not in order or not settings.research_fetch_playwright_enabled


def test_credits_exhausted_allows_fallback() -> None:
    assert is_fallback_eligible(BivFetchOutcomeCode.CREDITS_EXHAUSTED)


def test_robots_denied_blocks_fallback() -> None:
    from app.schemas.contracts import BivFetchOutcomeCode

    assert not is_fallback_eligible(BivFetchOutcomeCode.ROBOTS_BLOCKED)
    assert not is_fallback_eligible(
        BivFetchOutcomeCode.PROVIDER_REJECTED,
        error_class="robots_denied",
    )


@pytest.mark.asyncio
async def test_firecrawl_credits_exhausted_jina_success(monkeypatch) -> None:
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
    settings.research_fetch_provider_order = "firecrawl,jina,trafilatura"

    async def _mcp_fetch(*, url: str):
        raise BusinessToolError(category="credits_exhausted", message="402")

    body = (
        "Russian SaaS marketing automation market shows growing demand for AI-assisted "
        "campaign planning among small and medium businesses with subscription pricing."
    )

    async def _jina_fetch(self, request: FetchRequest):
        return _trafilatura_success_result(request, body=body, title="Jina title")

    monkeypatch.setattr(
        "app.business_idea_validation.research_fetch.providers.jina.JinaReaderFetchAdapter.fetch",
        _jina_fetch,
    )

    orchestrator = BivFetchOrchestrator(
        session,
        settings,
        run_id=uuid4(),
        correlation_id="corr-jina",
        metrics=BivPipelineMetricsRecorder(),
    )
    result = await orchestrator.fetch_url(
        "https://example.com/saas-market",
        query_id="q-jina",
        mcp_fetch=_mcp_fetch,
    )
    assert result.success is True
    assert result.fallback_used is True
    assert any(row.provider == "jina" and row.outcome_code == "success" for row in appended)


@pytest.mark.asyncio
async def test_duplicate_url_uses_cache(monkeypatch) -> None:
    session = AsyncMock()
    appended: list = []

    async def _capture_append(self, row):
        appended.append(row)
        row.id = uuid4()
        return row

    from app.db.repositories import biv_fetch_ledger as ledger_mod

    monkeypatch.setattr(ledger_mod.BivFetchLedgerRepository, "append", _capture_append)
    settings = get_settings()
    _configure_fetch_chain(settings)
    calls = {"n": 0}

    async def _jina_fetch(self, request: FetchRequest):
        calls["n"] += 1
        body = (
            "Enterprise demand for AI marketing tools continues to grow among mid-market SaaS "
            "companies with measurable retention outcomes and repeatable onboarding playbooks."
        )
        return _trafilatura_success_result(request, body=body)

    monkeypatch.setattr(
        "app.business_idea_validation.fetch_orchestrator.BivFetchOrchestrator._fetch_firecrawl",
        AsyncMock(
            side_effect=lambda *a, **k: (
                BivFetchOutcomeCode.CREDITS_EXHAUSTED,
                None,
                None,
                "",
                None,
                None,
                None,
            )
        ),
    )
    monkeypatch.setattr(
        "app.business_idea_validation.research_fetch.providers.trafilatura.LocalTrafilaturaFetchAdapter.fetch",
        _jina_fetch,
    )

    orchestrator = BivFetchOrchestrator(
        session,
        settings,
        run_id=uuid4(),
        correlation_id="corr-dedup",
        metrics=BivPipelineMetricsRecorder(),
    )
    first = await orchestrator.fetch_url("https://example.com/report")
    second = await orchestrator.fetch_url("https://example.com/report")
    assert first.success is True
    assert second.success is True
    assert calls["n"] == 1
    assert any(row.outcome_code == "duplicate_url" for row in appended)


@pytest.mark.asyncio
async def test_jina_malformed_url_rejected() -> None:
    from app.business_idea_validation.research_fetch.providers.jina import JinaReaderFetchAdapter

    settings = get_settings()
    adapter = JinaReaderFetchAdapter(settings)
    req = FetchRequest(
        tenant_id=None,
        research_run_id=uuid4(),
        source_url="http://127.0.0.1/secret",
        normalized_url="http://127.0.0.1/secret",
        requested_at=utc_now(),
        timeout_seconds=5.0,
        max_content_bytes=10000,
    )
    result = await adapter.fetch(req)
    assert result.status == ResearchFetchStatus.UNSAFE_URL


@pytest.mark.asyncio
async def test_jina_empty_markdown_failure(monkeypatch) -> None:
    from app.business_idea_validation.research_fetch.providers.jina import JinaReaderFetchAdapter

    class _Resp:
        status_code = 200
        text = "   "

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers=None):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client())
    settings = get_settings()
    adapter = JinaReaderFetchAdapter(settings)
    req = FetchRequest(
        tenant_id=None,
        research_run_id=uuid4(),
        source_url="https://example.com",
        normalized_url="https://example.com",
        requested_at=utc_now(),
        timeout_seconds=5.0,
        max_content_bytes=10000,
    )
    result = await adapter.fetch(req)
    assert result.status == ResearchFetchStatus.EMPTY_CONTENT


@pytest.mark.asyncio
async def test_tavily_missing_key_unavailable() -> None:
    from app.business_idea_validation.research_fetch.providers.tavily import TavilyExtractFetchAdapter

    settings = get_settings()
    adapter = TavilyExtractFetchAdapter(settings)
    with patch.object(settings, "tavily_api_key", None):
        assert adapter.is_available() is False


def test_provider_smoke_requires_fetch_contour() -> None:
    from app.business_idea_validation.real_research_readiness import provider_smoke_passed

    ok, _ = provider_smoke_passed({"status": "partially_ready", "fetch_contour": {"pass": True}})
    assert ok is True
    ok, blocker = provider_smoke_passed(
        {"status": "partially_ready", "fetch_contour": {"pass": False, "blocked_reason": "no_provider"}}
    )
    assert ok is False
    assert "no_provider" in (blocker or "")
