"""Avito product skill — installed_unconfigured until credentials exist; no live calls."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidStateError
from app.product_skills.permissions import assert_tool_allowed
from app.product_skills.secret_binding import all_aliases_configured
from app.schemas.contracts import ProductSkillManifest


def avito_credentials_present() -> bool:
    return all_aliases_configured(["AVITO_CLIENT_ID", "AVITO_CLIENT_SECRET"])


def avito_live_ready() -> bool:
    """Live Avito API is intentionally disabled in this slice — credentials alone ≠ runnable."""
    return False


def avito_configured() -> bool:
    """True only when the skill can honestly succeed at live reads (not merely env-bound)."""
    return avito_credentials_present() and avito_live_ready()


def avito_analytics_read(manifest: ProductSkillManifest, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    assert_tool_allowed(manifest, "avito.analytics.read")
    if not avito_credentials_present():
        raise InvalidStateError("avito_unconfigured")
    # Live API intentionally not implemented in this slice.
    raise InvalidStateError("avito_live_disabled_until_owner_credentials_verified")


def avito_account_read(manifest: ProductSkillManifest, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    assert_tool_allowed(manifest, "avito.account.read")
    if not avito_credentials_present():
        raise InvalidStateError("avito_unconfigured")
    raise InvalidStateError("avito_live_disabled_until_owner_credentials_verified")


def avito_write_blocked(manifest: ProductSkillManifest, tool_name: str) -> None:
    # Any write tool name is denied in MVP
    raise InvalidStateError("avito_write_disabled")
