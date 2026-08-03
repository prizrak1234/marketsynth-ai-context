"""LLM timeout/retry normalization tests — no network calls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.core.exceptions import ExecutorError
from app.llm.contracts import LLMGenerateInput, LLMMessage
from app.llm.errors import (
    LLMAuthenticationError,
    LLMBadRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
    format_llm_error,
    normalize_provider_error,
    sanitize_error_message,
)
from app.llm.litellm_adapter import LiteLLMAdapter
from app.llm.mock_adapter import MOCK_CONTENT, MockLLMAdapter
from app.llm.retry import LLMRetryPolicy, with_llm_retries
from app.schemas.contracts import LLMProvider
from fastapi.testclient import TestClient


def test_timeout_normalizes_to_llm_timeout_error() -> None:
    error = normalize_provider_error(
        TimeoutError("request timed out"),
        provider=LLMProvider.OPENAI,
        model="gpt-4o-mini",
    )
    assert isinstance(error, LLMTimeoutError)
    assert error.provider == "openai"
    assert error.model == "gpt-4o-mini"
    assert error.original_error_type == "TimeoutError"


@pytest.mark.asyncio
async def test_rate_limit_is_retried_expected_number_of_times() -> None:
    call = AsyncMock(
        side_effect=[
            LLMRateLimitError("rate limited", provider=LLMProvider.OPENAI, model="gpt-4o-mini"),
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

    assert result.value == "ok"
    assert result.retry_count == 2
    assert call.await_count == 3


@pytest.mark.asyncio
async def test_authentication_error_is_not_retried() -> None:
    call = AsyncMock(
        side_effect=LLMAuthenticationError(
            "invalid key",
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        ),
    )
    policy = LLMRetryPolicy(max_retries=2, timeout_seconds=5, backoff_base_seconds=0.01)

    with (
        patch("app.llm.retry.asyncio.sleep", new=AsyncMock()),
        pytest.raises(LLMAuthenticationError),
    ):
        await with_llm_retries(
            call,
            policy,
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )

    assert call.await_count == 1


@pytest.mark.asyncio
async def test_bad_request_is_not_retried() -> None:
    call = AsyncMock(
        side_effect=LLMBadRequestError(
            "bad payload",
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        ),
    )
    policy = LLMRetryPolicy(max_retries=2, timeout_seconds=5, backoff_base_seconds=0.01)

    with (
        patch("app.llm.retry.asyncio.sleep", new=AsyncMock()),
        pytest.raises(LLMBadRequestError),
    ):
        await with_llm_retries(
            call,
            policy,
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
        )

    assert call.await_count == 1


def test_secrets_are_redacted_in_error_message() -> None:
    sanitized = sanitize_error_message("Auth failed with api_key=sk-secret-value")
    assert "sk-" not in sanitized
    assert "api_key" not in sanitized.lower() or "redacted" in sanitized.lower()


@pytest.mark.asyncio
async def test_litellm_adapter_missing_key_raises_authentication_error() -> None:
    adapter = LiteLLMAdapter()
    with patch(
        "app.llm.litellm_adapter.get_provider_runtime_config",
        return_value=SimpleNamespace(
            api_key=None,
            timeout_seconds=60,
            max_retries=2,
        ),
    ), pytest.raises(LLMAuthenticationError, match="Missing API key"):
        await adapter.generate(
            LLMGenerateInput(
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini",
                messages=[LLMMessage(role="user", content="hello")],
            ),
        )


def test_executor_receives_safe_llm_error(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Retry Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "researcher"},
        headers=auth_headers,
    )
    agent_id = agent.json()["id"]
    run = client.post(
        "/agent-runs",
        json={"agent_id": agent_id, "input_payload": {"prompt": "safe fail"}},
        headers=auth_headers,
    )
    run_id = run.json()["id"]

    auth_error = LLMAuthenticationError(
        "Provider error (details redacted)",
        provider=LLMProvider.MOCK,
        model="mock-model",
        original_error_type="AuthenticationError",
    )
    with patch(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        new=AsyncMock(side_effect=auth_error),
    ):
        response = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "sk-" not in detail
    assert format_llm_error(auth_error) in detail

    failed_run = client.get(f"/agent-runs/{run_id}", headers=auth_headers).json()
    assert failed_run["status"] == "failed"
    assert "sk-" not in failed_run["error"]

    llm_request = client.get(
        "/llm-requests",
        params={"agent_run_id": run_id},
        headers=auth_headers,
    ).json()[0]
    assert llm_request["status"] == "failed"
    assert "sk-" not in llm_request["error"]


@pytest.mark.asyncio
async def test_mock_adapter_is_unchanged() -> None:
    adapter = MockLLMAdapter()
    output = await adapter.generate(
        LLMGenerateInput(
            provider=LLMProvider.MOCK,
            model="mock-model",
            messages=[LLMMessage(role="user", content="hello")],
        ),
    )
    assert output.content == MOCK_CONTENT
    assert output.provider == LLMProvider.MOCK


def test_format_llm_error_never_includes_secrets() -> None:
    error = LLMAuthenticationError(
        sanitize_error_message("bad api_key=sk-secret"),
        provider=LLMProvider.OPENAI,
        model="gpt-4o-mini",
    )
    formatted = format_llm_error(error)
    assert "sk-" not in formatted


def test_executor_error_still_raised_for_non_llm_failures(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/projects", json={"name": "Runtime Project"}, headers=auth_headers)
    agent = client.post(
        "/agents",
        json={"project_id": project.json()["id"], "type": "researcher"},
        headers=auth_headers,
    )
    run_id = client.post(
        "/agent-runs",
        json={"agent_id": agent.json()["id"], "input_payload": {"prompt": "boom"}},
        headers=auth_headers,
    ).json()["id"]

    with patch(
        "app.llm.mock_adapter.MockLLMAdapter.generate",
        new=AsyncMock(side_effect=RuntimeError("adapter exploded")),
    ):
        response = client.post(f"/agent-runs/{run_id}/execute-dry-run", headers=auth_headers)

    assert response.status_code == 500
    with pytest.raises(ExecutorError):
        raise ExecutorError(response.json()["detail"])
