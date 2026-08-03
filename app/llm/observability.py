"""LLM call observability — metrics, events, cost placeholders."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from app.core.logging import get_logger
from app.llm.contracts import LLMGenerateOutput
from app.llm.errors import LLMError
from app.llm.secrets_boundary import assert_no_sensitive_keys, redact_sensitive_payload
from app.schemas.contracts import LLMProvider

LLMCallStatus = Literal["succeeded", "failed"]


@dataclass(frozen=True)
class LLMCallMetrics:
    provider: str
    model: str
    latency_ms: int
    retry_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: Decimal | None
    error_type: str | None
    status: LLMCallStatus

    def to_log_payload(self) -> dict[str, Any]:
        payload = {
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "retry_count": self.retry_count,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": (
                str(self.estimated_cost_usd) if self.estimated_cost_usd is not None else None
            ),
            "error_type": self.error_type,
            "status": self.status,
        }
        assert_no_sensitive_keys(payload)
        return payload

    def to_metadata(self) -> dict[str, Any]:
        return self.to_log_payload()


def estimate_llm_cost(
    *,
    provider: LLMProvider | str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal | None:
    """Cost placeholder — real pricing will be added in a later phase."""
    _ = (provider, model, prompt_tokens, completion_tokens)
    return None


def metrics_from_output(output: LLMGenerateOutput) -> LLMCallMetrics:
    if isinstance(output.provider, LLMProvider):
        provider = output.provider.value
    else:
        provider = str(output.provider)
    return LLMCallMetrics(
        provider=provider,
        model=output.model or "",
        latency_ms=output.latency_ms or 0,
        retry_count=output.retry_count,
        prompt_tokens=int(output.usage.get("input_tokens", 0)),
        completion_tokens=int(output.usage.get("output_tokens", 0)),
        total_tokens=int(output.usage.get("total_tokens", 0)),
        estimated_cost_usd=output.estimated_cost_usd,
        error_type=None,
        status="succeeded",
    )


def metrics_from_error(
    exc: LLMError,
    *,
    latency_ms: int | None,
    retry_count: int,
) -> LLMCallMetrics:
    return LLMCallMetrics(
        provider=exc.provider,
        model=exc.model,
        latency_ms=latency_ms or 0,
        retry_count=retry_count,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        estimated_cost_usd=None,
        error_type=type(exc).__name__,
        status="failed",
    )


def log_llm_event(event_name: str, payload: Mapping[str, Any]) -> None:
    safe_payload = redact_sensitive_payload(dict(payload))
    if isinstance(safe_payload, dict):
        get_logger("app.llm").info(event_name, **safe_payload)
        return
    get_logger("app.llm").info(event_name, payload=safe_payload)


@asynccontextmanager
async def measure_llm_call(
    *,
    provider: LLMProvider | str,
    model: str,
) -> AsyncIterator[dict[str, Any]]:
    provider_value = provider.value if isinstance(provider, LLMProvider) else str(provider)
    state: dict[str, Any] = {"retry_count": 0, "started_at": time.perf_counter()}
    log_llm_event(
        "llm.call.started",
        {"provider": provider_value, "model": model},
    )
    try:
        yield state
    except LLMError as exc:
        latency_ms = int((time.perf_counter() - state["started_at"]) * 1000)
        exc.latency_ms = latency_ms
        exc.retry_count = int(state.get("retry_count", 0))
        metrics = metrics_from_error(
            exc,
            latency_ms=latency_ms,
            retry_count=exc.retry_count,
        )
        payload = metrics.to_log_payload()
        payload["safe_message"] = exc.safe_message
        log_llm_event("llm.call.failed", payload)
        raise
    except Exception:
        latency_ms = int((time.perf_counter() - state["started_at"]) * 1000)
        log_llm_event(
            "llm.call.failed",
            {
                "provider": provider_value,
                "model": model,
                "latency_ms": latency_ms,
                "retry_count": int(state.get("retry_count", 0)),
                "error_type": "UnexpectedError",
                "status": "failed",
            },
        )
        raise
