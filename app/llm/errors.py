"""Domain LLM errors — safe messages only, no secrets."""

from __future__ import annotations

import asyncio

from app.schemas.contracts import LLMProvider

SECRET_MARKERS = ("sk-", "api_key", "authorization", "bearer ")


def sanitize_error_message(message: str) -> str:
    text = message.strip()
    if not text:
        return "Provider error"
    lowered = text.lower()
    if any(marker in lowered for marker in SECRET_MARKERS):
        return "Provider error (details redacted)"
    return text


class LLMError(Exception):
    def __init__(
        self,
        safe_message: str,
        *,
        provider: LLMProvider | str,
        model: str,
        original_error_type: str | None = None,
    ) -> None:
        self.provider = provider.value if isinstance(provider, LLMProvider) else str(provider)
        self.model = model
        self.safe_message = sanitize_error_message(safe_message)
        self.original_error_type = original_error_type
        self.retry_count = 0
        self.latency_ms: int | None = None
        super().__init__(self.safe_message)

    def __str__(self) -> str:
        return self.safe_message


class LLMTimeoutError(LLMError):
    """Provider call exceeded the configured timeout."""


class LLMRateLimitError(LLMError):
    """Provider rate limit reached."""


class LLMAuthenticationError(LLMError):
    """Provider rejected credentials."""


class LLMProviderUnavailableError(LLMError):
    """Provider is temporarily unavailable."""


class LLMBadRequestError(LLMError):
    """Request payload rejected by provider."""


class LLMUnknownProviderError(LLMError):
    """Provider is not supported by the adapter layer."""


def format_llm_error(error: LLMError) -> str:
    prefix = f"[{error.provider}/{error.model}]"
    if error.original_error_type:
        return f"{prefix} {error.safe_message} ({error.original_error_type})"
    return f"{prefix} {error.safe_message}"


def normalize_provider_error(
    exc: BaseException,
    *,
    provider: LLMProvider,
    model: str,
) -> LLMError:
    original_type = type(exc).__name__

    if isinstance(exc, LLMError):
        return exc

    if isinstance(exc, asyncio.TimeoutError):
        return LLMTimeoutError(
            "LLM request timed out",
            provider=provider,
            model=model,
            original_error_type=original_type,
        )

    litellm_errors = _load_litellm_exception_types()
    if litellm_errors is not None:
        mapped = _map_litellm_exception(exc, provider=provider, model=model, types=litellm_errors)
        if mapped is not None:
            return mapped

    lowered_name = original_type.lower()
    lowered_message = str(exc).lower()
    if "timeout" in lowered_name or "timeout" in lowered_message:
        return LLMTimeoutError(
            "LLM request timed out",
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    if "ratelimit" in lowered_name or "rate limit" in lowered_message:
        return LLMRateLimitError(
            "LLM provider rate limit exceeded",
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    if "auth" in lowered_name or "unauthorized" in lowered_message or "401" in lowered_message:
        return LLMAuthenticationError(
            "LLM provider authentication failed",
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    if "badrequest" in lowered_name or "invalid" in lowered_message or "400" in lowered_message:
        return LLMBadRequestError(
            "LLM provider rejected the request",
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    if "unavailable" in lowered_name or "connection" in lowered_name or "503" in lowered_message:
        return LLMProviderUnavailableError(
            "LLM provider is unavailable",
            provider=provider,
            model=model,
            original_error_type=original_type,
        )

    return LLMError(
        sanitize_error_message(str(exc)),
        provider=provider,
        model=model,
        original_error_type=original_type,
    )


def _load_litellm_exception_types() -> dict[str, type[BaseException]] | None:
    try:
        from litellm.exceptions import (
            AuthenticationError,
            BadRequestError,
            RateLimitError,
            ServiceUnavailableError,
            Timeout,
        )
    except ImportError:
        return None

    return {
        "Timeout": Timeout,
        "RateLimitError": RateLimitError,
        "AuthenticationError": AuthenticationError,
        "BadRequestError": BadRequestError,
        "ServiceUnavailableError": ServiceUnavailableError,
    }


def _map_litellm_exception(
    exc: BaseException,
    *,
    provider: LLMProvider,
    model: str,
    types: dict[str, type[BaseException]],
) -> LLMError | None:
    original_type = type(exc).__name__
    message = str(exc) or "Provider error"

    if isinstance(exc, types["Timeout"]):
        return LLMTimeoutError(
            message,
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    if isinstance(exc, types["RateLimitError"]):
        return LLMRateLimitError(
            message,
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    if isinstance(exc, types["AuthenticationError"]):
        return LLMAuthenticationError(
            message,
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    if isinstance(exc, types["BadRequestError"]):
        return LLMBadRequestError(
            message,
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    if isinstance(exc, types["ServiceUnavailableError"]):
        return LLMProviderUnavailableError(
            message,
            provider=provider,
            model=model,
            original_error_type=original_type,
        )
    return None
