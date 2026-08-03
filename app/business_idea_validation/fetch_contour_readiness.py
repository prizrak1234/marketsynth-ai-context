"""Fetch contour readiness — degraded vs unavailable."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from app.core.config import Settings, get_settings


class FetchContourState(StrEnum):
    READY = "ready"
    DEGRADED_BUT_OPERATIONAL = "degraded_but_operational"
    UNAVAILABLE = "unavailable"


async def assess_fetch_contour(
    settings: Settings | None = None,
    *,
    live: bool = True,
) -> dict[str, Any]:
    """Evaluate multi-provider fetch contour without exposing secrets."""
    s = settings or get_settings()
    if s.research_source_collection_mock_providers:
        return {
            "state": FetchContourState.UNAVAILABLE.value,
            "pass": False,
            "mock": True,
            "providers": {},
            "operational_providers": [],
            "degraded_providers": [],
            "blocked_reason": "mock_providers_enabled",
        }

    from app.business_idea_validation.research_fetch.policy import parse_provider_order
    from app.business_idea_validation.research_fetch.registry import probe_fetch_provider
    from app.research_source_collection.readiness import _probe_firecrawl

    order = parse_provider_order(s)
    provider_rows: dict[str, Any] = {}
    operational: list[str] = []
    degraded: list[str] = []

    for name in order:
        if name == "firecrawl":
            if not (s.firecrawl_api_key and s.firecrawl_api_key.get_secret_value().strip()):
                provider_rows[name] = {"state": "misconfigured", "ok": False}
                continue
            if live:
                row = (await _probe_firecrawl(s)).model_dump(mode="json")
            else:
                row = {"state": "partially_ready", "configured": True}
            ok = row.get("state") == "ready"
            provider_rows[name] = row
            if ok:
                operational.append(name)
            elif row.get("safe_error_code") == "credits_exhausted":
                degraded.append(name)
            continue

        if name == "tavily":
            adapter_ok = bool(s.tavily_api_key and s.tavily_api_key.get_secret_value().strip())
            if not adapter_ok:
                provider_rows[name] = {"state": "misconfigured", "ok": False}
                continue

        if name == "playwright" and not s.research_fetch_playwright_enabled:
            provider_rows[name] = {"state": "disabled", "ok": False}
            continue

        if live and name in {"jina", "trafilatura", "direct_http"}:
            probe = await probe_fetch_provider(name if name != "direct_http" else "trafilatura", s)
            ok = bool(probe.get("ok"))
            provider_rows[name] = {"state": "ready" if ok else "unavailable", "ok": ok, **probe}
            if ok:
                operational.append(name)
            continue

        if name in {"trafilatura", "direct_http", "jina"}:
            provider_rows[name] = {"state": "ready", "ok": True, "probed": False}
            operational.append(name)

    if operational:
        state = (
            FetchContourState.READY
            if "firecrawl" in operational
            else FetchContourState.DEGRADED_BUT_OPERATIONAL
        )
        return {
            "state": state.value,
            "pass": True,
            "mock": False,
            "providers": provider_rows,
            "operational_providers": operational,
            "degraded_providers": degraded,
            "provider_order": order,
        }

    return {
        "state": FetchContourState.UNAVAILABLE.value,
        "pass": False,
        "mock": False,
        "providers": provider_rows,
        "operational_providers": [],
        "degraded_providers": degraded,
        "blocked_reason": "no_operational_fetch_provider",
    }
