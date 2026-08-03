"""Tavily Extract fetch adapter — extract-only, not research verdict."""

from __future__ import annotations

import hashlib

import httpx

from app.business_idea_validation.research_fetch.mapping import invalid_url_status
from app.business_idea_validation.research_fetch.port import (
    FetchRequest,
    FetchResult,
    ResearchFetchStatus,
)
from app.business_idea_validation.research_fetch.security import validate_fetch_url
from app.business_tools.contracts import BusinessToolError
from app.core.config import Settings
from app.db.base import utc_now


class TavilyExtractFetchAdapter:
    provider_name = "tavily"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        key = self._settings.tavily_api_key
        return bool(key and key.get_secret_value().strip())

    async def fetch(self, request: FetchRequest) -> FetchResult:
        if not self.is_available():
            raise BusinessToolError("not_configured", "Tavily is not configured.")
        started = utc_now()
        url = request.normalized_url
        safe, code = validate_fetch_url(url)
        if not safe:
            return _fail_result(
                self.provider_name,
                request,
                status=invalid_url_status(code),
                safe_error_code=code,
                started=started,
            )
        api_key = self._settings.tavily_api_key
        assert api_key is not None
        token = api_key.get_secret_value().strip()
        depth = "basic" if self._settings.tavily_extract_depth != "advanced" else "advanced"
        payload = {"urls": [url], "extract_depth": depth, "include_images": False}
        timeout = request.timeout_seconds
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    "https://api.tavily.com/extract",
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise BusinessToolError("timeout", "Tavily Extract timed out.") from exc
        except Exception as exc:  # noqa: BLE001
            raise BusinessToolError("provider_unavailable", "Tavily Extract unavailable.") from exc

        latency_ms = int((utc_now() - started).total_seconds() * 1000)
        if resp.status_code == 429:
            return _fail_result(
                self.provider_name,
                request,
                status=ResearchFetchStatus.RATE_LIMITED,
                safe_error_code="rate_limited",
                started=started,
                http_status=429,
                latency_ms=latency_ms,
            )
        if resp.status_code in {401, 403}:
            return _fail_result(
                self.provider_name,
                request,
                status=ResearchFetchStatus.PROVIDER_UNAVAILABLE,
                safe_error_code="auth_error",
                started=started,
                http_status=resp.status_code,
                latency_ms=latency_ms,
            )
        if resp.status_code != 200:
            return _fail_result(
                self.provider_name,
                request,
                status=ResearchFetchStatus.UNKNOWN_FAILURE,
                safe_error_code=f"http_{resp.status_code}",
                started=started,
                http_status=resp.status_code,
                latency_ms=latency_ms,
            )

        data = resp.json() if resp.content else {}
        results = (data or {}).get("results") or []
        text = ""
        title: str | None = None
        for row in results:
            if str(row.get("url") or "") == url or not text:
                text = str(row.get("raw_content") or row.get("content") or "")
                title = str(row.get("title") or "")[:300] or None
        text = text.strip()
        if not text:
            return _fail_result(
                self.provider_name,
                request,
                status=ResearchFetchStatus.EMPTY_CONTENT,
                safe_error_code="empty_content",
                started=started,
                http_status=200,
                latency_ms=latency_ms,
            )
        if len(text.encode("utf-8", errors="ignore")) > request.max_content_bytes:
            text = text[: request.max_content_bytes]
        content_hash = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        attempt = int(request.trace_context.get("attempt_number", "1"))
        return FetchResult(
            provider=self.provider_name,
            source_url=request.source_url,
            final_url=url,
            normalized_url=request.normalized_url,
            fetched_at=utc_now(),
            status=ResearchFetchStatus.SUCCEEDED,
            http_status=200,
            content_type="text/plain",
            title=title,
            raw_html=None,
            extracted_text=text,
            markdown=None,
            language=None,
            content_hash=content_hash,
            byte_count=len(text.encode("utf-8", errors="ignore")),
            latency_ms=latency_ms,
            attempt_number=attempt,
        )


def _fail_result(
    provider: str,
    request: FetchRequest,
    *,
    status: ResearchFetchStatus,
    safe_error_code: str,
    started,
    http_status: int | None = None,
    latency_ms: int | None = None,
) -> FetchResult:
    if latency_ms is None:
        latency_ms = int((utc_now() - started).total_seconds() * 1000)
    attempt = int(request.trace_context.get("attempt_number", "1"))
    return FetchResult(
        provider=provider,
        source_url=request.source_url,
        final_url=request.normalized_url,
        normalized_url=request.normalized_url,
        fetched_at=utc_now(),
        status=status,
        http_status=http_status,
        content_type=None,
        title=None,
        raw_html=None,
        extracted_text="",
        markdown=None,
        language=None,
        content_hash="",
        byte_count=0,
        latency_ms=latency_ms,
        attempt_number=attempt,
        safe_error_code=safe_error_code,
    )
