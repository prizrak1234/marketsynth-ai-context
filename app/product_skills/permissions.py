"""Default-deny permission checks for product skills."""

from __future__ import annotations

from app.core.exceptions import InvalidStateError
from app.schemas.contracts import ProductSkillExternalAction, ProductSkillManifest


def assert_tool_allowed(manifest: ProductSkillManifest, tool_name: str) -> None:
    if tool_name not in manifest.allowed_tools:
        raise InvalidStateError(f"permission_denied: tool {tool_name}")


def assert_host_allowed(manifest: ProductSkillManifest, host: str) -> None:
    allowed = {h.lower() for h in manifest.allowed_network_hosts}
    if host.lower() not in allowed:
        raise InvalidStateError(f"permission_denied: network {host}")


def assert_write_allowed(manifest: ProductSkillManifest) -> None:
    if manifest.external_action != ProductSkillExternalAction.WRITE:
        raise InvalidStateError("permission_denied: external write disabled")
    if not manifest.human_approval_required:
        raise InvalidStateError("permission_denied: write requires human approval flag")
