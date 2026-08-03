"""Phase AI.70 — Publishing provider abstraction."""

from __future__ import annotations

import pytest
from app.core.exceptions import InvalidStateError
from app.publishing.providers.contracts import PublishingProviderType
from app.publishing.providers.registry import get_provider, resolve_provider_type_for_channel


def test_resolve_provider_type_telegram_only() -> None:
    assert resolve_provider_type_for_channel("telegram") == PublishingProviderType.TELEGRAM
    with pytest.raises(InvalidStateError, match="not enabled"):
        resolve_provider_type_for_channel("instagram")


def test_dry_run_provider_always_available() -> None:
    provider = get_provider(PublishingProviderType.DRY_RUN)
    assert provider is not None
