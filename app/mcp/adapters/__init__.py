"""Provider-neutral MCP adapter interfaces."""

from __future__ import annotations

from typing import Protocol

from app.business_tools.contracts import SourceFetchResult, WebSearchResult


class SearchMcpAdapter(Protocol):
    async def search(self, query: str, *, limit: int = 5) -> WebSearchResult: ...


class FetchMcpAdapter(Protocol):
    async def fetch(self, url: str) -> SourceFetchResult: ...
