"""Webhook publishing channel config — validation and safe previews (Phase 6.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.core.exceptions import InvalidStateError
from app.events.delivery_url import build_target_url_preview
from app.llm.secrets_boundary import find_sensitive_key, redact_sensitive_payload


@dataclass(frozen=True)
class WebhookChannelConfig:
    url: str
    signing_secret: str | None = None
    headers: dict[str, str] | None = None


def _require_non_empty_str(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidStateError(f"Webhook channel config field '{field}' must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise InvalidStateError(f"Webhook channel config field '{field}' is required")
    return cleaned


def _validate_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidStateError("Webhook channel url must use http or https")
    if not parsed.hostname:
        raise InvalidStateError("Webhook channel url must include a host")
    return url


def _normalize_headers(raw: object) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise InvalidStateError("Webhook channel config field 'headers' must be an object")
    normalized: dict[str, str] = {}
    for key, value in raw.items():
        key_str = str(key).strip()
        if not key_str:
            raise InvalidStateError("Webhook channel header names cannot be empty")
        if not isinstance(value, str):
            raise InvalidStateError(
                f"Webhook channel header '{key_str}' must be a string value",
            )
        normalized[key_str] = value.strip()
    return normalized


def validate_webhook_channel_config(config: dict[str, Any] | None) -> WebhookChannelConfig:
    """Validate and normalize webhook channel config for persistence."""
    if not config:
        raise InvalidStateError("Webhook channel config requires 'url'")

    url = _validate_http_url(_require_non_empty_str(config.get("url"), field="url"))

    signing_secret_raw = config.get("signing_secret")
    signing_secret: str | None = None
    if signing_secret_raw is not None:
        signing_secret = _require_non_empty_str(signing_secret_raw, field="signing_secret")

    headers = _normalize_headers(config.get("headers"))

    return WebhookChannelConfig(
        url=url,
        signing_secret=signing_secret,
        headers=headers or None,
    )


def webhook_channel_config_to_dict(config: WebhookChannelConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {"url": config.url}
    if config.signing_secret is not None:
        payload["signing_secret"] = config.signing_secret
    if config.headers:
        payload["headers"] = dict(config.headers)
    return payload


def _redact_headers_for_preview(headers: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in headers.items():
        key_str = str(key)
        if find_sensitive_key({key_str: value}) is not None:
            redacted[key_str] = "***"
        else:
            redacted[key_str] = value
    return redacted


def build_webhook_config_preview(config: dict[str, Any] | None) -> dict[str, Any]:
    """API-safe preview: no signing_secret, no URL query, no secret-like header values."""
    if not config:
        return {}
    preview = redact_sensitive_payload(dict(config))
    if not isinstance(preview, dict):
        return {}
    url = preview.get("url")
    if isinstance(url, str) and url.strip():
        preview["url"] = build_target_url_preview(url)
    headers = preview.get("headers")
    if isinstance(headers, dict):
        preview["headers"] = _redact_headers_for_preview(headers)
    return preview
