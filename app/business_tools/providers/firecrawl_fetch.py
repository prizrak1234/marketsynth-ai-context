"""Firecrawl read-only source fetch adapter (Phase H2.7).

Read-only. Fetches a single approved URL and returns a normalized Source
CANDIDATE. Never recursive-crawls, never auto-accepts as Evidence, never
produces a BusinessVerdict. Not wired to an executable research skill in slice 1.
"""

from __future__ import annotations

from typing import Any

from app.business_tools.contracts import (
    BusinessToolError,
    SourceCandidate,
    SourceFetchResult,
)
from app.core.config import Settings, get_settings

_PROBE_URL = "https://example.com"


class FirecrawlFetchTool:
    provider_name = "firecrawl"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _api_key(self) -> str:
        key = self._settings.firecrawl_api_key
        val = key.get_secret_value().strip() if key else ""
        if not val:
            raise BusinessToolError("not_configured", "Firecrawl is not configured.")
        return val

    async def fetch(self, url: str) -> SourceFetchResult:
        """Fetch a single URL (no crawling). Returns a Source candidate."""
        key = self._api_key()
        target = (url or "").strip()
        if not target.startswith("http"):
            raise BusinessToolError("invalid_url", "A valid http(s) URL is required.")
        import httpx

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"url": target, "formats": ["markdown"]},
                )
        except Exception as exc:  # noqa: BLE001
            raise BusinessToolError("provider_unavailable", "Fetch provider unavailable.") from exc
        _raise_for_http_status(resp.status_code)

        data = resp.json() if resp.content else {}
        payload = (data or {}).get("data") or {}
        markdown = str(payload.get("markdown") or "")[:2000]
        meta = payload.get("metadata") or {}
        candidate = SourceCandidate(
            url=target[:1000],
            title=str(meta.get("title") or "")[:300],
            snippet=markdown[:400],
            provider=self.provider_name,
            is_evidence=False,
        )
        return SourceFetchResult(
            url=target,
            provider=self.provider_name,
            candidate=candidate,
            normalized_text_excerpt=markdown,
            warnings=["candidate_only_not_evidence", "no_recursive_crawl"],
        )

    async def probe(self) -> dict[str, Any]:
        """Single read-only fetch for readiness — uses stable public URL."""
        result = await self.fetch(_PROBE_URL)
        excerpt = (result.normalized_text_excerpt or "").strip()
        return {
            "ok": len(excerpt) >= 10,
            "rate_limit_state": "ok",
        }


def _raise_for_http_status(status_code: int) -> None:
    if status_code in {401, 403}:
        raise BusinessToolError("invalid_credentials", "Fetch authentication failed.")
    if status_code == 402:
        raise BusinessToolError("credits_exhausted", "Fetch credits exhausted.")
    if status_code == 429:
        raise BusinessToolError("rate_limited", "Fetch rate limit reached.")
    if status_code != 200:
        raise BusinessToolError("provider_error", f"Fetch http_{status_code}.")
