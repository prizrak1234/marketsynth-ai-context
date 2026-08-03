"""BusinessTool registry (Phase H2.7).

Resolves a normalized BusinessToolCode to a concrete provider, honoring the
Integration Registry readiness. Read-only tools only in slice 1. External
execution (Make/n8n) and advertising writes are never resolvable here.
"""

from __future__ import annotations

from app.business_tools.contracts import BusinessToolError
from app.core.config import Settings, get_settings
from app.integrations.registry import get_integration
from app.schemas.contracts import (
    BusinessToolCode,
    IntegrationCode,
    IntegrationReadiness,
)

# Only these normalized tools are resolvable in slice 1. Execution/advertising
# tools are intentionally absent — they require an approval boundary.
_READONLY_TOOLS = frozenset(
    {
        BusinessToolCode.WEB_SEARCH,
        BusinessToolCode.SOURCE_FETCH,
    }
)


def _ensure_configured(code: IntegrationCode, settings: Settings) -> None:
    integ = get_integration(code, settings)
    if integ is None or not integ.configured:
        raise BusinessToolError("not_configured", f"{code.value} is not configured.")
    if integ.readiness in {IntegrationReadiness.BLOCKED, IntegrationReadiness.DISABLED}:
        # Disabled read-only adapters can still be constructed for explicit,
        # owner-approved diagnostics, but blocked ones cannot.
        if integ.readiness == IntegrationReadiness.BLOCKED:
            raise BusinessToolError("blocked", f"{code.value} is blocked.")


def get_web_search_tool(settings: Settings | None = None):
    s = settings or get_settings()
    _ensure_configured(IntegrationCode.XMLRIVER, s)
    from app.business_tools.providers.xmlriver_search import XmlRiverSearchTool

    return XmlRiverSearchTool(s)


def get_source_fetch_tool(settings: Settings | None = None):
    s = settings or get_settings()
    _ensure_configured(IntegrationCode.FIRECRAWL, s)
    from app.business_tools.providers.firecrawl_fetch import FirecrawlFetchTool

    return FirecrawlFetchTool(s)


def resolve_business_tool(code: BusinessToolCode, settings: Settings | None = None):
    if code not in _READONLY_TOOLS:
        raise BusinessToolError(
            "not_resolvable",
            f"Tool {code.value} is not resolvable in this phase (approval boundary).",
        )
    if code == BusinessToolCode.WEB_SEARCH:
        return get_web_search_tool(settings)
    if code == BusinessToolCode.SOURCE_FETCH:
        return get_source_fetch_tool(settings)
    raise BusinessToolError("not_resolvable", f"Tool {code.value} not resolvable.")
