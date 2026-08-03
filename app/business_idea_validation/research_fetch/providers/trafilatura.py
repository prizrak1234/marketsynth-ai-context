"""Local HTTP fetch + Trafilatura extraction — credit-free fallback."""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.business_idea_validation.research_fetch.mapping import invalid_url_status
from app.business_idea_validation.research_fetch.port import (
    FetchRequest,
    FetchResult,
    ResearchFetchStatus,
)
from app.business_idea_validation.research_fetch.security import (
    resolve_host_is_public,
    validate_fetch_url,
    validate_redirect_target,
)
from app.business_tools.contracts import BusinessToolError
from app.core.config import Settings
from app.db.base import utc_now

_MAX_REDIRECTS = 5
_SAFE_UA = "MarketsynthResearchBot/1.0 (+read-only)"


class LocalTrafilaturaFetchAdapter:
    provider_name = "trafilatura"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        return True

    async def fetch(self, request: FetchRequest) -> FetchResult:
        started = utc_now()
        url = request.normalized_url
        safe, code = validate_fetch_url(url)
        if not safe:
            return _fail(
                request,
                status=invalid_url_status(code),
                safe_error_code=code or "invalid_url",
                started=started,
            )
        parsed_host = httpx.URL(url).host
        if parsed_host:
            public, dns_code = resolve_host_is_public(parsed_host)
            if not public:
                return _fail(
                    request,
                    status=ResearchFetchStatus.UNSAFE_URL,
                    safe_error_code=dns_code or "unsafe_url",
                    started=started,
                )

        final_url, http_status, content_type, raw_html = await self._safe_get(
            url,
            timeout=request.timeout_seconds,
            max_bytes=request.max_content_bytes,
        )
        latency_ms = int((utc_now() - started).total_seconds() * 1000)
        if http_status != 200:
            status = _http_to_status(http_status)
            return _fail(
                request,
                status=status,
                safe_error_code=f"http_{http_status}",
                started=started,
                http_status=http_status,
                latency_ms=latency_ms,
            )

        title, text = _extract_with_trafilatura(raw_html, final_url)
        if not (text or "").strip():
            return _fail(
                request,
                status=ResearchFetchStatus.EMPTY_CONTENT,
                safe_error_code="empty_content",
                started=started,
                http_status=http_status,
                latency_ms=latency_ms,
            )
        text = text.strip()
        content_hash = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        attempt = int(request.trace_context.get("attempt_number", "1"))
        return FetchResult(
            provider=self.provider_name,
            source_url=request.source_url,
            final_url=final_url,
            normalized_url=request.normalized_url,
            fetched_at=utc_now(),
            status=ResearchFetchStatus.SUCCEEDED,
            http_status=http_status,
            content_type=content_type,
            title=title,
            raw_html=raw_html[:2000] if raw_html else None,
            extracted_text=text,
            markdown=None,
            language=None,
            content_hash=content_hash,
            byte_count=len(text.encode("utf-8", errors="ignore")),
            latency_ms=latency_ms,
            attempt_number=attempt,
        )

    async def _safe_get(
        self,
        url: str,
        *,
        timeout: float,
        max_bytes: int,
    ) -> tuple[str, int, str, str]:
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            safe, code = validate_fetch_url(current)
            if not safe:
                raise BusinessToolError(code or "unsafe_url", "URL blocked by security policy.")
            host = httpx.URL(current).host
            if host:
                public, dns_code = resolve_host_is_public(host)
                if not public:
                    raise BusinessToolError(dns_code or "unsafe_url", "Blocked host.")
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                headers={"User-Agent": _SAFE_UA},
            ) as client:
                resp = await client.get(current)
            if resp.status_code in {301, 302, 303, 307, 308}:
                location = resp.headers.get("location")
                if not location:
                    return current, resp.status_code, "", ""
                next_url = str(httpx.URL(current).join(location))
                ok, _ = validate_redirect_target(next_url)
                if not ok:
                    raise BusinessToolError("unsafe_url", "Redirect target blocked.")
                current = next_url
                continue
            raw_bytes = resp.content[:max_bytes]
            try:
                raw_html = raw_bytes.decode(resp.encoding or "utf-8", errors="replace")
            except LookupError:
                raw_html = raw_bytes.decode("utf-8", errors="replace")
            ct = resp.headers.get("content-type", "")[:128]
            if ct and "html" not in ct.lower() and "text" not in ct.lower():
                raise BusinessToolError("unsupported_content_type", "Unsupported content type.")
            return current, resp.status_code, ct, raw_html
        raise BusinessToolError("provider_error", "Too many redirects.")


def _extract_with_trafilatura(html: str, url: str) -> tuple[str | None, str]:
    try:
        import trafilatura

        downloaded = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        meta = trafilatura.extract_metadata(html, default_url=url)
        title = meta.title if meta and meta.title else None
        if downloaded and downloaded.strip():
            return title, downloaded
    except ImportError:
        pass
    except Exception:  # noqa: BLE001
        pass
    return _regex_fallback(html)


def _regex_fallback(html: str) -> tuple[str | None, str]:
    import re

    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I | re.S)
    title = title_match.group(1).strip()[:300] if title_match else None
    stripped = re.sub(
        r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.I | re.S,
    )
    text = re.sub(r"<[^>]+>", " ", stripped)
    text = " ".join(text.split())
    return title, text


def _http_to_status(code: int) -> ResearchFetchStatus:
    if code == 404:
        return ResearchFetchStatus.NOT_FOUND
    if code == 429:
        return ResearchFetchStatus.RATE_LIMITED
    if code == 403:
        return ResearchFetchStatus.BLOCKED
    if code >= 500:
        return ResearchFetchStatus.PROVIDER_UNAVAILABLE
    return ResearchFetchStatus.UNKNOWN_FAILURE


def _fail(
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
        provider="trafilatura",
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


async def probe_trafilatura_fetch(settings: Settings) -> dict[str, Any]:
    import uuid

    adapter = LocalTrafilaturaFetchAdapter(settings)
    started = utc_now()
    req = FetchRequest(
        tenant_id=None,
        research_run_id=uuid.uuid4(),
        source_url="https://example.com",
        normalized_url="https://example.com",
        requested_at=started,
        timeout_seconds=settings.research_fetch_timeout_seconds,
        max_content_bytes=settings.research_fetch_max_content_bytes,
    )
    result = await adapter.fetch(req)
    return {
        "ok": result.status == ResearchFetchStatus.SUCCEEDED,
        "http_status": result.http_status,
        "latency_ms": result.latency_ms,
        "extracted_len": len(result.extracted_text),
        "safe_error_code": result.safe_error_code,
    }
