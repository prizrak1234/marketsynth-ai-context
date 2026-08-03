"""REAL-RESEARCH-HARDENING-01 — fetch ledger, pipeline gates, baseline regression."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.business_idea_validation.fetch_circuit_breaker import (
    CircuitState,
    FetchCircuitRegistry,
    ProviderCircuit,
)
from app.business_idea_validation.fetch_outcomes import (
    classify_extracted_body,
    is_retryable,
    map_business_tool_error,
    map_http_status,
)
from app.business_idea_validation.pipeline_metrics import BivPipelineMetricsRecorder
from app.business_idea_validation.pipeline_validator import (
    classify_baseline_8038e2a7,
    validate_pipeline,
)
from app.schemas.contracts import (
    BivFetchOutcomeCode,
    BivPipelineMetrics,
    BusinessIdeaValidationConfidence,
    BusinessIdeaValidationOutput,
    BusinessIdeaValidationVerdictKind,
)


def test_baseline_8038e2a7_classified_as_fetch_zero_success() -> None:
    """Incident run 8038e2a7: search=32, fetch=0 must hard-fail."""
    result = classify_baseline_8038e2a7(search=32, fetch_success=0)
    assert result.passed is False
    assert result.failure is not None
    assert result.failure.failure_code == "pipeline_fetch_zero_success"
    assert result.failure.failure_stage == "fetch"
    assert result.failure.retryable is True


def test_fetch_success_rate_uses_attempted_eligible_urls() -> None:
    metrics = BivPipelineMetricsRecorder()
    metrics.record_fetch_eligible()
    metrics.record_fetch_eligible()
    url_a = "https://example.com/a"
    url_b = "https://example.com/b"
    metrics.record_fetch_attempt(BivFetchOutcomeCode.RATE_LIMITED, normalized_url=url_a)
    metrics.record_fetch_attempt(BivFetchOutcomeCode.SUCCESS, normalized_url=url_a)
    metrics.record_fetch_attempt(BivFetchOutcomeCode.HTTP_403, normalized_url=url_b)
    data = metrics.data
    assert data.fetch.fetch_attempts == 3
    assert data.fetch.fetch_success_count == 1
    assert data.fetch.attempted_eligible_urls == 2
    assert data.fetch.fetch_success_rate == 0.5
    assert data.fetch.failures_by_outcome["rate_limited"] == 1
    assert data.fetch.failures_by_outcome.get("success") is None


def test_outcome_mapping_retryable() -> None:
    assert is_retryable(BivFetchOutcomeCode.HTTP_429) is True
    assert is_retryable(BivFetchOutcomeCode.HTTP_403) is False
    assert map_http_status(429) == BivFetchOutcomeCode.HTTP_429
    assert map_business_tool_error("rate_limited") == BivFetchOutcomeCode.RATE_LIMITED


def test_classify_extracted_body_rejects_dom_and_empty() -> None:
    assert classify_extracted_body("") == BivFetchOutcomeCode.EMPTY_CONTENT
    assert classify_extracted_body("short") == BivFetchOutcomeCode.CONTENT_TOO_SHORT
    assert (
        classify_extracted_body("x" * 120, content_type="text/html")
        == BivFetchOutcomeCode.SUCCESS
    )


def test_circuit_breaker_opens_after_threshold() -> None:
    registry = FetchCircuitRegistry()
    circuit = registry.get("firecrawl")
    circuit.failure_threshold = 3
    for _ in range(3):
        circuit.record_failure()
    assert circuit.state == CircuitState.OPEN
    assert circuit.allow_request() is False


def test_circuit_breaker_half_open_after_cooldown(monkeypatch) -> None:
    circuit = ProviderCircuit(failure_threshold=1, open_seconds=0.01)
    circuit.record_failure()
    assert circuit.state == CircuitState.OPEN
    import time

    time.sleep(0.02)
    assert circuit.allow_request() is True
    assert circuit.state == CircuitState.HALF_OPEN
    circuit.record_success()
    assert circuit.state == CircuitState.CLOSED


def test_validate_pipeline_blocks_search_without_fetch() -> None:
    metrics = BivPipelineMetrics()
    metrics.discovery.search_success_count = 5
    metrics.fetch.fetch_success_count = 0
    metrics.fetch.fetch_attempts = 10
    output = BusinessIdeaValidationOutput(
        investigation_id=uuid4(),
        verdict=BusinessIdeaValidationVerdictKind.INSUFFICIENT_EVIDENCE,
        mcp_search_calls=5,
        mcp_fetch_calls=0,
        confidence=BusinessIdeaValidationConfidence(total_score=10),
    )
    result = validate_pipeline(output, metrics, require_customer_report=False)
    assert result.passed is False
    assert result.failure is not None
    assert result.failure.failure_code == "pipeline_fetch_zero_success"


def test_fetch_ledger_entry_contract_mapping() -> None:
    from app.db.models.biv_fetch_ledger import BivFetchLedgerTable
    from app.db.repositories.biv_fetch_ledger import BivFetchLedgerRepository

    run_id = uuid4()
    fetch_id = uuid4()
    now = datetime.now(UTC)
    row = BivFetchLedgerTable(
        id=fetch_id,
        run_id=run_id,
        correlation_id="corr-test",
        query_id="q1",
        source_url="https://example.com/page",
        normalized_url="https://example.com/page",
        provider="firecrawl",
        attempt_number=1,
        started_at=now,
        finished_at=now,
        latency_ms=120,
        http_status=429,
        outcome_code=BivFetchOutcomeCode.RATE_LIMITED.value,
        retryable=True,
        fallback_used=False,
        safe_error_message="Provider rate limit reached.",
        extracted_text_length=0,
        created_at=now,
    )
    entry = BivFetchLedgerRepository.to_contract(row)
    assert entry.fetch_id == fetch_id
    assert entry.outcome_code == BivFetchOutcomeCode.RATE_LIMITED
    assert entry.retryable is True
