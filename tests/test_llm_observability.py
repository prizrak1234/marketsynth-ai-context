"""LLM observability tests — metrics, metadata, events; no network calls."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from app.llm.contracts import LLMGenerateInput, LLMGenerateOutput, LLMMessage
from app.llm.errors import LLMAuthenticationError, LLMRateLimitError
from app.llm.mock_adapter import MOCK_CONTENT, MockLLMAdapter
from app.llm.observability import (
    LLMCallMetrics,
    estimate_llm_cost,
    log_llm_event,
    metrics_from_error,
    metrics_from_output,
)
from app.llm.retry import LLMRetryPolicy, with_llm_retries
from app.schemas.contracts import LLMProvider
from fastapi.testclient import TestClient


def test_estimate_llm_cost_returns_none_placeholder() -> None:
    assert (
        estimate_llm_cost(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=5,
        )
        is None
    )


def test_metrics_from_output_includes_latency_and_retry_count() -> None:
    output = LLMGenerateOutput(
        content="ok",
        provider=LLMProvider.MOCK,
        model="mock-model",
        usage={"input_tokens": 3, "output_tokens": 7, "total_tokens": 10},
        latency_ms=42,
        retry_count=2,
        estimated_cost_usd=None,
    )
    metrics = metrics_from_output(output)
    assert metrics.latency_ms == 42
    assert metrics.retry_count == 2
    assert metrics.prompt_tokens == 3
    assert metrics.completion_tokens == 7
    assert metrics.total_tokens == 10
    assert metrics.estimated_cost_usd is None


@pytest.mark.asyncio
async def test_retry_count_propagates_through_retry_result() -> None:
    call = AsyncMock(
        side_effect=[
            LLMRateLimitError("rate limited", provider=LLMProvider.OPENAI, model="gpt-4o-mini"),
            "ok",
        ],
    )
    policy = LLMRetryPolicy(
        max_retries=2,
        timeout_seconds=5,
        backoff_base_seconds=0.01,
        backoff_max_seconds=0.02,
    )
    with patch("app.llm.retry.asyncio.sleep", new=AsyncMock()):
        result = await with_llm_retries(
            call,
            policy,
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )
    assert result.retry_count == 1


def test_failed_llm_error_metadata_is_safe() -> None:
    error = LLMAuthenticationError(
        "Provider error (details redacted)",
        provider=LLMProvider.OPENAI,
        model="gpt-4o-mini",
        original_error_type="AuthenticationError",
    )
    metrics = metrics_from_error(error, latency_ms=120, retry_count=1)
    metadata = metrics.to_metadata()
    assert metadata["status"] == "failed"
    assert metadata["error_type"] == "LLMAuthenticationError"
    assert metadata["latency_ms"] == 120
    assert metadata["retry_count"] == 1
    assert "sk-" not in str(metadata).lower()


def test_log_llm_event_redacts_secrets() -> None:
    with patch("app.llm.observability.get_logger") as logger_factory:
        logger = logger_factory.return_value
        log_llm_event(
            "llm.call.failed",
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "sk-secret",
                "status": "failed",
            },
        )
    logger.info.assert_called_once()
    payload = logger.info.call_args.kwargs
    assert payload["api_key"] == "***"


@pytest.mark.asyncio
async def test_mock_adapter_sets_observability_fields() -> None:
    adapter = MockLLMAdapter()
    output = await adapter.generate(
        LLMGenerateInput(
            provider=LLMProvider.MOCK,
            model="mock-model",
            messages=[LLMMessage(role="user", content="hello")],
        ),
    )
    assert output.content == MOCK_CONTENT
    assert output.latency_ms is not None
    assert output.latency_ms >= 0
    assert output.retry_count == 0
    assert output.estimated_cost_usd is None
    assert output.raw_response == {}


def test_executor_persists_observability_metadata_on_success(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Obs Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "researcher"},
        headers=auth_headers,
    )
    run = client.post(
        "/agent-runs",
        json={"agent_id": agent.json()["id"], "input_payload": {"prompt": "observe"}},
        headers=auth_headers,
    )
    run_id = run.json()["id"]
    execute = client.post(
        f"/agent-runs/{run_id}/execute-dry-run",
        headers=auth_headers,
    )
    assert execute.status_code == 200

    llm_request = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()[0]
    assert llm_request["request_metadata"]["latency_ms"] >= 0
    assert llm_request["request_metadata"]["retry_count"] == 0
    assert llm_request["request_metadata"]["estimated_cost_usd"] is None

    detail = client.get(f"/llm-requests/{llm_request['id']}", headers=auth_headers).json()
    assert detail["response"]["latency_ms"] >= 0
    assert detail["response"]["raw_response"] == {}
    assert detail["response"]["response_metadata"]["retry_count"] == 0
    assert "sk-" not in str(detail).lower()


def test_executor_persists_safe_failure_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Obs Fail Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "researcher"},
        headers=auth_headers,
    )
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent.json()["id"], "input_payload": {"prompt": "fail"}},
        headers=auth_headers,
    ).json()["id"]

    auth_error = LLMAuthenticationError(
        "Provider error (details redacted)",
        provider=LLMProvider.MOCK,
        model="mock-model",
        original_error_type="AuthenticationError",
    )
    auth_error.latency_ms = 55
    auth_error.retry_count = 0

    with patch(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        new=AsyncMock(side_effect=auth_error),
    ):
        client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)

    llm_request = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()[0]
    assert llm_request["status"] == "failed"
    assert llm_request["request_metadata"]["error_type"] == "LLMAuthenticationError"
    assert llm_request["request_metadata"]["latency_ms"] == 55
    assert "sk-" not in str(llm_request).lower()


def test_llm_call_metrics_to_metadata_serializes_decimal() -> None:
    metrics = LLMCallMetrics(
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=10,
        retry_count=0,
        prompt_tokens=1,
        completion_tokens=2,
        total_tokens=3,
        estimated_cost_usd=Decimal("0.001"),
        error_type=None,
        status="succeeded",
    )
    assert metrics.to_metadata()["estimated_cost_usd"] == "0.001"
