"""Reject secrets in publishing channel config (Phase AI.60)."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidStateError

_FORBIDDEN_KEY_FRAGMENTS = (
    "token",
    "secret",
    "api_key",
    "apikey",
    "password",
    "credential",
    "bearer",
    "authorization",
    "private_key",
    "access_key",
)


def _key_is_forbidden(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(fragment in lowered for fragment in _FORBIDDEN_KEY_FRAGMENTS)


def _walk(value: object, path: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_str = str(key)
            full_path = f"{path}.{key_str}" if path else key_str
            if _key_is_forbidden(key_str):
                raise InvalidStateError(
                    f"Forbidden secret-like key in config_metadata: {full_path}",
                )
            _walk(nested, full_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk(item, f"{path}[{index}]")


def sanitize_channel_config_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {}
    _walk(raw, "")
    return dict(raw)
