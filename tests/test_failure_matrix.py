"""Failure matrix integration tests for fetch orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.business_idea_validation.fetch_circuit_breaker import get_fetch_circuit_registry
from app.business_idea_validation.fetch_orchestrator import BivFetchOrchestrator
from app.business_idea_validation.pipeline_metrics import BivPipelineMetricsRecorder
from app.business_idea_validation.research_fetch.port import FetchRequest, FetchResult, ResearchFetchStatus
from app.business_tools.contracts import BusinessToolError
from app.core.config import get_settings
from app.db.base import utc_now
from app.schemas.contracts import BivFetchOutcomeCode
import hashlib


@pytest.fixture(autouse=True)
def _reset_circuits():
    reg = get_fetch_circuit_registry()
    reg._circuits.clear()
    yield
    reg._circuits.clear()


def _open_firecrawl_circuit() -> None:
    circuit = get_fetch_circuit_registry().get("firecrawl")
    for _ in range(circuit.failure_threshold):
        circuit.record_failure()


def _fail_result(request: FetchRequest, *, status: ResearchFetchStatus, code: str, http_status: int | None) -> FetchResult:
    return FetchResult(
        provider="trafilatura",
        source_url=request.source_url,
        final_url=request.normalized_url,
        normalized_url=request.normalized_url,
        fetched_at=utc_now(),
        status=status,
        http_status=http_status,
        content_type="text/html",
        title=None,
        raw_html=None,
        extracted_text="",
        markdown=None,
        language=None,
        content_hash="",
        byte_count=0,
        latency_ms=5,
        attempt_number=1,
        safe_error_code=code,
    )


async def _orchestrator(monkeypatch) -> tuple[BivFetchOrchestrator, list]:
    session = AsyncMock()
    appended: list = []

    async def _capture(self, row):
        appended.append(row)
        row.id = uuid4()
        return row

    from app.db.repositories import biv_fetch_ledger as ledger_mod

    monkeypatch.setattr(ledger_mod.BivFetchLedgerRepository, "append", _capture)
    settings = get_settings()
    settings.research_fetch_provider_order = "firecrawl,trafilatura"
    orch = BivFetchOrchestrator(
        session,
        settings,
        run_id=uuid4(),
        correlation_id="matrix",
        metrics=BivPipelineMetricsRecorder(),
    )
    return orch, appended


@pytest.mark.asyncio
async def test_matrix_primary_429_fallback_success(monkeypatch) -> None:
    orch, appended = await _orchestrator(monkeypatch)

    async def _mcp(*, url: str):
        raise BusinessToolError("rate_limited", "429")

    body = (
        "Enterprise demand for AI marketing automation continues to grow among mid-market "
        "SaaS companies with measurable retention outcomes and onboarding playbooks."
    )

    async def _traf(self, request: FetchRequest):
        text = body
        return FetchResult(
            provider="trafilatura",
            source_url=request.source_url,
            final_url=request.normalized_url,
            normalized_url=request.normalized_url,
            fetched_at=utc_now(),
            status=ResearchFetchStatus.SUCCEEDED,
            http_status=200,
            content_type="text/html",
            title="T",
            raw_html=None,
            extracted_text=text,
            markdown=None,
            language=None,
            content_hash=hashlib.sha256(text.encode()).hexdigest(),
            byte_count=len(text.encode()),
            latency_ms=5,
            attempt_number=1,
        )

    monkeypatch.setattr(
        "app.business_idea_validation.research_fetch.providers.trafilatura.LocalTrafilaturaFetchAdapter.fetch",
        _traf,
    )
    result = await orch.fetch_url("https://example.com/a", mcp_fetch=_mcp)
    assert result.success is True
    assert appended


@pytest.mark.asyncio
async def test_matrix_direct_http_403(monkeypatch) -> None:
    _open_firecrawl_circuit()
    orch, appended = await _orchestrator(monkeypatch)

    async def _traf(self, request: FetchRequest):
        return _fail_result(request, status=ResearchFetchStatus.BLOCKED, code="http_403", http_status=403)

    monkeypatch.setattr(
        "app.business_idea_validation.research_fetch.providers.trafilatura.LocalTrafilaturaFetchAdapter.fetch",
        _traf,
    )
    result = await orch.fetch_url("https://example.com/forbidden", mcp_fetch=None)
    assert result.success is False
    assert result.outcome == BivFetchOutcomeCode.HTTP_403
    assert appended


@pytest.mark.asyncio
async def test_matrix_empty_page_not_success(monkeypatch) -> None:
    _open_firecrawl_circuit()
    orch, _ = await _orchestrator(monkeypatch)

    async def _traf(self, request: FetchRequest):
        return FetchResult(
            provider="trafilatura",
            source_url=request.source_url,
            final_url=request.normalized_url,
            normalized_url=request.normalized_url,
            fetched_at=utc_now(),
            status=ResearchFetchStatus.SUCCEEDED,
            http_status=200,
            content_type="text/html",
            title="",
            raw_html="<html><body></body></html>",
            extracted_text="",
            markdown=None,
            language=None,
            content_hash="",
            byte_count=0,
            latency_ms=5,
            attempt_number=1,
        )

    monkeypatch.setattr(
        "app.business_idea_validation.research_fetch.providers.trafilatura.LocalTrafilaturaFetchAdapter.fetch",
        _traf,
    )
    result = await orch.fetch_url("https://example.com/empty", mcp_fetch=None)
    assert result.success is False
    assert result.outcome in {
        BivFetchOutcomeCode.EMPTY_CONTENT,
        BivFetchOutcomeCode.CONTENT_TOO_SHORT,
    }


@pytest.mark.asyncio
async def test_matrix_js_shell_not_success(monkeypatch) -> None:
    _open_firecrawl_circuit()
    orch, _ = await _orchestrator(monkeypatch)

    async def _traf(self, request: FetchRequest):
        raw = "Enable JavaScript to view this page."
        return FetchResult(
            provider="trafilatura",
            source_url=request.source_url,
            final_url=request.normalized_url,
            normalized_url=request.normalized_url,
            fetched_at=utc_now(),
            status=ResearchFetchStatus.SUCCEEDED,
            http_status=200,
            content_type="text/html",
            title="",
            raw_html=raw,
            extracted_text=raw,
            markdown=None,
            language=None,
            content_hash=hashlib.sha256(raw.encode()).hexdigest(),
            byte_count=len(raw.encode()),
            latency_ms=5,
            attempt_number=1,
        )

    monkeypatch.setattr(
        "app.business_idea_validation.research_fetch.providers.trafilatura.LocalTrafilaturaFetchAdapter.fetch",
        _traf,
    )
    result = await orch.fetch_url("https://example.com/js", mcp_fetch=None)
    assert result.success is False
    assert result.outcome == BivFetchOutcomeCode.JAVASCRIPT_REQUIRED
