"""Resolve media generation providers with feature gates (Phase AI.56–AI.57)."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.media_generation.contracts import MediaGenerationProvider
from app.media_generation.mock_provider import MockImageGenerationProvider


def assert_provider_selectable(provider: MediaGenerationProvider, settings: Settings) -> None:
    if provider == MediaGenerationProvider.MOCK:
        return
    if provider == MediaGenerationProvider.FLUX:
        raise InvalidStateError("Flux media generation is not available in this phase")
    if provider == MediaGenerationProvider.OPENAI_IMAGES:
        if not settings.media_generation_enabled:
            raise InvalidStateError("Media generation is disabled")
        if not settings.openai_images_enabled:
            raise InvalidStateError("OpenAI Images provider is disabled")
        if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value().strip():
            raise InvalidStateError("OpenAI API key is not configured")
        return
    raise InvalidStateError(f"Unsupported media generation provider: {provider.value}")


def get_image_provider(
    provider: MediaGenerationProvider,
    settings: Settings,
) -> MockImageGenerationProvider | object:
    assert_provider_selectable(provider, settings)
    if provider == MediaGenerationProvider.MOCK:
        return MockImageGenerationProvider()
    if provider == MediaGenerationProvider.OPENAI_IMAGES:
        from app.media_generation.openai_images_provider import OpenAIImagesProvider

        return OpenAIImagesProvider(settings)
    raise InvalidStateError(f"Provider not implemented: {provider.value}")
