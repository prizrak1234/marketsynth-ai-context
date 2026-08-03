"""Provider adapter registry."""

from __future__ import annotations

from typing import Any

from app.business_idea_validation.research_fetch.port import ResearchFetchPort
from app.business_idea_validation.research_fetch.providers.jina import JinaReaderFetchAdapter
from app.business_idea_validation.research_fetch.providers.playwright import (
    PlaywrightReadabilityFetchAdapter,
)
from app.business_idea_validation.research_fetch.providers.tavily import TavilyExtractFetchAdapter
from app.business_idea_validation.research_fetch.providers.trafilatura import (
    LocalTrafilaturaFetchAdapter,
)
from app.core.config import Settings


def build_fetch_adapters(settings: Settings) -> dict[str, ResearchFetchPort]:
    adapters: dict[str, ResearchFetchPort] = {
        "jina": JinaReaderFetchAdapter(settings),
        "tavily": TavilyExtractFetchAdapter(settings),
        "trafilatura": LocalTrafilaturaFetchAdapter(settings),
        "direct_http": LocalTrafilaturaFetchAdapter(settings),
        "playwright": PlaywrightReadabilityFetchAdapter(settings),
    }
    return adapters


async def probe_fetch_provider(name: str, settings: Settings) -> dict[str, Any]:
    if name in {"trafilatura", "direct_http"}:
        from app.business_idea_validation.research_fetch.providers.trafilatura import (
            probe_trafilatura_fetch,
        )

        row = await probe_trafilatura_fetch(settings)
        row["provider"] = name
        return row
    if name == "jina":
        from app.business_idea_validation.research_fetch.providers.jina import probe_jina_reader

        row = await probe_jina_reader(settings)
        row["provider"] = name
        return row
    return {"provider": name, "ok": False, "safe_error_code": "not_probed"}
