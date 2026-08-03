"""Secret alias → Settings binding (never store values in skill packages)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class SecretBindingResult:
    alias: str
    configured: bool
    # Never expose value outside trusted tool boundary
    _value: str | None = None

    @property
    def value(self) -> str | None:
        return self._value


# Package alias → Settings attribute
_ALIAS_MAP: dict[str, str] = {
    "XML_RIVER_USER_ID": "xmlriver_user_id",
    "XML_RIVER_KEY": "xmlriver_api_key",
    "XMLRIVER_USER_ID": "xmlriver_user_id",
    "XMLRIVER_API_KEY": "xmlriver_api_key",
    "AVITO_CLIENT_ID": "avito_client_id",
    "AVITO_CLIENT_SECRET": "avito_client_secret",
}


def resolve_secret_alias(
    alias: str,
    settings: Settings | None = None,
) -> SecretBindingResult:
    settings = settings or get_settings()
    attr = _ALIAS_MAP.get(alias)
    if attr is None:
        return SecretBindingResult(alias=alias, configured=False, _value=None)
    raw = getattr(settings, attr, None)
    if raw is None:
        return SecretBindingResult(alias=alias, configured=False, _value=None)
    if hasattr(raw, "get_secret_value"):
        value = raw.get_secret_value()
    else:
        value = str(raw).strip() if raw else ""
    configured = bool(value)
    return SecretBindingResult(
        alias=alias,
        configured=configured,
        _value=value if configured else None,
    )


def all_aliases_configured(aliases: list[str], settings: Settings | None = None) -> bool:
    if not aliases:
        return True
    settings = settings or get_settings()
    return all(resolve_secret_alias(a, settings).configured for a in aliases)
