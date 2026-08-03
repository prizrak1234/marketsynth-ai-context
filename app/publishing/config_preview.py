"""Redact channel config for API responses — no secrets in config_preview."""

from __future__ import annotations

from typing import Any

from app.llm.secrets_boundary import redact_sensitive_payload
from app.publishing.contracts import PublishingChannelType
from app.publishing.telegram_channel_config import build_telegram_config_preview
from app.publishing.webhook_channel_config import build_webhook_config_preview


def build_config_preview(
    config: dict[str, Any] | None,
    *,
    channel_type: PublishingChannelType | None = None,
) -> dict[str, Any]:
    """Return a compact, redacted copy safe for HTTP responses."""
    if not config:
        return {}
    if channel_type == PublishingChannelType.WEBHOOK:
        return build_webhook_config_preview(config)
    if channel_type == PublishingChannelType.TELEGRAM:
        return build_telegram_config_preview(config)
    redacted = redact_sensitive_payload(dict(config))
    if not isinstance(redacted, dict):
        return {}
    return redacted
