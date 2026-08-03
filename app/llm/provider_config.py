"""Runtime provider credentials and call limits — secrets stay in Settings only."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.core.config import Settings, get_settings
from app.core.exceptions import ExecutorError
from app.schemas.contracts import LLMProvider


class ProviderRuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: LLMProvider
    api_key: str | None = None
    timeout_seconds: int
    max_retries: int


def _read_secret(value: object | None) -> str | None:
    if value is None:
        return None
    raw = value.get_secret_value() if hasattr(value, "get_secret_value") else value
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def get_provider_runtime_config(
    provider: LLMProvider,
    settings: Settings | None = None,
) -> ProviderRuntimeConfig:
    resolved_settings = settings or get_settings()

    if provider == LLMProvider.MOCK:
        api_key = None
    elif provider == LLMProvider.OPENAI:
        api_key = _read_secret(resolved_settings.openai_api_key)
    elif provider == LLMProvider.ANTHROPIC:
        api_key = _read_secret(resolved_settings.anthropic_api_key)
    elif provider == LLMProvider.GOOGLE:
        api_key = _read_secret(resolved_settings.google_api_key)
    elif provider == LLMProvider.DEEPSEEK:
        api_key = _read_secret(resolved_settings.deepseek_api_key)
    elif provider == LLMProvider.LOCAL:
        api_key = None
    else:
        raise ExecutorError(f"Unsupported LLM provider: {provider.value}")

    return ProviderRuntimeConfig(
        provider=provider,
        api_key=api_key,
        timeout_seconds=resolved_settings.llm_timeout_seconds,
        max_retries=resolved_settings.llm_max_retries,
    )
