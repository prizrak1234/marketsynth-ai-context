"""Firecrawl fetch adapter for WEB_FETCH_MCP role."""

from __future__ import annotations

from app.business_tools.contracts import SourceFetchResult
from app.business_tools.providers.firecrawl_fetch import FirecrawlFetchTool
from app.core.config import Settings


class FirecrawlFetchMcpAdapter:
    def __init__(self, settings: Settings) -> None:
        self._tool = FirecrawlFetchTool(settings)

    async def fetch(self, url: str) -> SourceFetchResult:
        return await self._tool.fetch(url)
