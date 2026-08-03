"""XmlRiver search adapter for SEARCH_MCP role."""

from __future__ import annotations

from app.business_tools.contracts import WebSearchResult
from app.business_tools.providers.xmlriver_search import XmlRiverSearchTool
from app.core.config import Settings


class XmlRiverSearchMcpAdapter:
    def __init__(self, settings: Settings) -> None:
        self._tool = XmlRiverSearchTool(settings)

    async def search(self, query: str, *, limit: int = 5) -> WebSearchResult:
        return await self._tool.search(query, limit=limit)
