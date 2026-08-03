"""Commercial LLM provider gate for Content Factory copywriter generation."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.llm.config import resolve_llm_config
from app.llm.provider_config import get_provider_runtime_config
from app.schemas.contracts import ContentFactoryProviderReadiness, LLMProvider

_COMMERCIAL_LLM_PROVIDERS = frozenset({LLMProvider.OPENAI, LLMProvider.OPENROUTER})

_BLOCKED_MESSAGES_RU: dict[str, str] = {
    "mock_provider_not_commercial": "Генерация материалов временно недоступна: включён mock-провайдер.",
    "llm_provider_not_configured": "Генерация материалов временно недоступна: LLM-провайдер не настроен.",
    "llm_provider_not_supported": (
        "Генерация материалов временно недоступна: провайдер не поддерживает коммерческую генерацию."
    ),
}


def assess_content_factory_provider_readiness(
    settings: Settings | None = None,
) -> ContentFactoryProviderReadiness:
    resolved = settings or get_settings()
    provider, model, _, _ = resolve_llm_config({}, settings=resolved)

    if provider == LLMProvider.MOCK:
        return ContentFactoryProviderReadiness(
            ready=False,
            blocked_reason="mock_provider_not_commercial",
            blocked_message_ru=_BLOCKED_MESSAGES_RU["mock_provider_not_commercial"],
            provider=provider.value,
            model=model,
            mock_provider=True,
        )

    if provider not in _COMMERCIAL_LLM_PROVIDERS:
        return ContentFactoryProviderReadiness(
            ready=False,
            blocked_reason="llm_provider_not_supported",
            blocked_message_ru=_BLOCKED_MESSAGES_RU["llm_provider_not_supported"],
            provider=provider.value,
            model=model,
            mock_provider=False,
        )

    runtime = get_provider_runtime_config(provider, resolved)
    if not (runtime.api_key or "").strip():
        return ContentFactoryProviderReadiness(
            ready=False,
            blocked_reason="llm_provider_not_configured",
            blocked_message_ru=_BLOCKED_MESSAGES_RU["llm_provider_not_configured"],
            provider=provider.value,
            model=model,
            mock_provider=False,
        )

    return ContentFactoryProviderReadiness(
        ready=True,
        provider=provider.value,
        model=model,
        estimated_input_tokens_min=8_000,
        estimated_input_tokens_max=24_000,
        mock_provider=False,
    )
