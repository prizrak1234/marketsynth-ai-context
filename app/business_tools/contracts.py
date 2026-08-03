"""Normalized business tool contracts (Phase H2.7).

Specialists reference these normalized tools, never provider SDKs or secret
env var names. Providers are resolved behind the BusinessTool registry.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SourceCandidate(BaseModel):
    """A candidate source — NOT Evidence. Requires validation before use."""

    url: str
    title: str = ""
    snippet: str = ""
    provider: str = ""
    fetched_at: str | None = None
    is_evidence: bool = False


class WebSearchResult(BaseModel):
    query: str
    provider: str
    candidates: list[SourceCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SourceFetchResult(BaseModel):
    url: str
    provider: str
    candidate: SourceCandidate | None = None
    normalized_text_excerpt: str = ""
    warnings: list[str] = Field(default_factory=list)


class BusinessToolError(RuntimeError):
    """Raised when a tool is denied by policy or unavailable."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.user_message = message
