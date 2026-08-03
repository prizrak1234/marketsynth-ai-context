"""Publishing provider registry (Phase AI.70)."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidStateError
from app.publishing.providers.base import PublishingProvider
from app.publishing.providers.contracts import PublishingProviderType
from app.publishing.providers.dry_run_provider import get_dry_run_provider
from app.publishing.providers.telegram_provider import (
    assert_telegram_publishing_ready,
    get_telegram_provider,
)


def resolve_provider_type_for_channel(channel_type: str) -> PublishingProviderType:
    if channel_type == "telegram":
        return PublishingProviderType.TELEGRAM
    raise InvalidStateError("Real publishing is not enabled for this channel")


def get_provider(
    provider_type: PublishingProviderType,
    *,
    settings: Settings | None = None,
) -> PublishingProvider:
    if provider_type == PublishingProviderType.DRY_RUN:
        return get_dry_run_provider()
    if provider_type == PublishingProviderType.TELEGRAM:
        assert_telegram_publishing_ready(settings or get_settings())
        return get_telegram_provider(settings)
    raise InvalidStateError(f"Unsupported publishing provider: {provider_type.value}")
