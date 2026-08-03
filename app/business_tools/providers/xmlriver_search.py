"""XMLRiver read-only web search adapter (Phase H2.7).

Read-only. Returns Source CANDIDATES only — never Evidence, never a
BusinessVerdict. Not wired to an executable research skill in slice 1.
"""

from __future__ import annotations

from typing import Any

from app.business_tools.contracts import (
    BusinessToolError,
    SourceCandidate,
    WebSearchResult,
)
from app.core.config import Settings, get_settings

_PROBE_QUERY = "marketsynth provider readiness probe"


class XmlRiverSearchTool:
    provider_name = "xmlriver"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _credentials(self) -> tuple[str, str]:
        user = (self._settings.xmlriver_user_id or "").strip()
        key = self._settings.xmlriver_api_key
        key_val = key.get_secret_value().strip() if key else ""
        if not user or not key_val:
            raise BusinessToolError("not_configured", "XMLRiver is not configured.")
        return user, key_val

    async def search(self, query: str, *, limit: int = 5) -> WebSearchResult:
        """Perform a read-only search returning candidate sources."""
        user, key = self._credentials()
        cleaned = " ".join((query or "").split())[:512]
        if not cleaned:
            raise BusinessToolError("invalid_query", "Empty search query.")
        import httpx

        url = "http://xmlriver.com/search/xml"
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.get(
                    url,
                    params={"user": user, "key": key, "query": cleaned},
                )
        except Exception as exc:  # noqa: BLE001
            raise BusinessToolError("provider_unavailable", "Search provider unavailable.") from exc
        _raise_for_http_status(resp.status_code)

        candidates = _parse_candidates(resp.text, limit=limit)
        return WebSearchResult(
            query=cleaned,
            provider=self.provider_name,
            candidates=candidates,
            warnings=["candidates_only_not_evidence"],
        )

    async def probe(self) -> dict[str, Any]:
        """Single read-only search for readiness — never logs secrets."""
        result = await self.search(_PROBE_QUERY, limit=1)
        return {
            "result_count": len(result.candidates),
            "rate_limit_state": "ok" if result.candidates else "zero_results",
        }


def _raise_for_http_status(status_code: int) -> None:
    if status_code in {401, 403}:
        raise BusinessToolError("invalid_credentials", "Search authentication failed.")
    if status_code == 429:
        raise BusinessToolError("rate_limited", "Search rate limit reached.")
    if status_code != 200:
        raise BusinessToolError("provider_error", f"Search http_{status_code}.")


def _parse_candidates(xml_text: str, *, limit: int) -> list[SourceCandidate]:
    import re

    out: list[SourceCandidate] = []
    for match in re.finditer(r"<url>(.*?)</url>", xml_text, flags=re.I | re.S):
        raw = match.group(1).strip()
        if not raw:
            continue
        out.append(
            SourceCandidate(url=raw[:1000], provider="xmlriver", is_evidence=False)
        )
        if len(out) >= limit:
            break
    return out
