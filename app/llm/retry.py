"""Controlled LLM retry policy — no external retry frameworks."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from app.llm.errors import (
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
    normalize_provider_error,
)
from app.llm.observability import log_llm_event
from app.llm.provider_config import ProviderRuntimeConfig
from app.schemas.contracts import LLMProvider

T = TypeVar("T")

DEFAULT_RETRYABLE_ERRORS: frozenset[type[LLMError]] = frozenset(
    {
        LLMTimeoutError,
        LLMRateLimitError,
        LLMProviderUnavailableError,
    },
)


@dataclass(frozen=True)
class LLMRetryPolicy:
    max_retries: int
    timeout_seconds: int
    retryable_error_types: frozenset[type[LLMError]] = DEFAULT_RETRYABLE_ERRORS
    backoff_base_seconds: float = 0.5
    backoff_max_seconds: float = 8.0


@dataclass(frozen=True)
class LLMRetryResult[T]:
    value: T
    retry_count: int


def retry_policy_from_runtime(runtime: ProviderRuntimeConfig) -> LLMRetryPolicy:
    return LLMRetryPolicy(
        max_retries=runtime.max_retries,
        timeout_seconds=runtime.timeout_seconds,
    )


def _is_retryable(error: LLMError, policy: LLMRetryPolicy) -> bool:
    return isinstance(error, tuple(policy.retryable_error_types))


def _backoff_seconds(policy: LLMRetryPolicy, attempt: int) -> float:
    base = min(policy.backoff_base_seconds * (2 ** max(attempt - 1, 0)), policy.backoff_max_seconds)
    jitter = random.uniform(0, base * 0.1)
    return base + jitter


async def with_llm_retries[T](
    call: Callable[[], Awaitable[T]],
    policy: LLMRetryPolicy,
    *,
    provider: LLMProvider,
    model: str,
    retry_state: dict[str, int] | None = None,
) -> LLMRetryResult[T]:
    attempt = 0
    provider_value = provider.value
    while True:
        try:
            value = await asyncio.wait_for(call(), timeout=policy.timeout_seconds)
            retry_count = attempt
            if retry_state is not None:
                retry_state["retry_count"] = retry_count
            return LLMRetryResult(value=value, retry_count=retry_count)
        except LLMError as exc:
            normalized = exc
        except Exception as exc:
            normalized = normalize_provider_error(exc, provider=provider, model=model)

        if not _is_retryable(normalized, policy) or attempt >= policy.max_retries:
            normalized.retry_count = attempt
            if retry_state is not None:
                retry_state["retry_count"] = attempt
            raise normalized

        attempt += 1
        if retry_state is not None:
            retry_state["retry_count"] = attempt
        log_llm_event(
            "llm.call.retry",
            {
                "provider": provider_value,
                "model": model,
                "attempt": attempt,
                "max_retries": policy.max_retries,
                "error_type": type(normalized).__name__,
            },
        )
        await asyncio.sleep(_backoff_seconds(policy, attempt))
