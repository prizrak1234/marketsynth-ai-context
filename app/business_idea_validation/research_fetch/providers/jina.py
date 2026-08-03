"""Jina Reader external fetch adapter."""

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


class JinaReaderFetchAdapter:
    provider_name = "jina"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        return True

    async def fetch(self, request: FetchRequest) -> FetchResult:
        started = utc_now()
        url = request.normalized_url
        safe, code = validate_fetch_url(url)
        if not safe:
            return self._fail(
                request,
                status=invalid_url_status(code),
                safe_error_code=code or "invalid_url",
                started=started,
            )
        jina_url = f"https://r.jina.ai/{url}"
        headers: dict[str, str] = {"Accept": "text/markdown"}
        key = self._settings.jina_api_key
        if key and key.get_secret_value().strip():
            headers["Authorization"] = f"Bearer {key.get_secret_value().strip()}"
        timeout = request.timeout_seconds
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                resp = await client.get(jina_url, headers=headers)
        except httpx.TimeoutException as exc:
            raise BusinessToolError("timeout", "Jina Reader timed out.") from exc
        except Exception as exc:  # noqa: BLE001
            raise BusinessToolError("provider_unavailable", "Jina Reader unavailable.") from exc

        latency_ms = int((utc_now() - started).total_seconds() * 1000)
        if resp.status_code == 429:
            return self._fail(
                request,
                status=ResearchFetchStatus.RATE_LIMITED,
                safe_error_code="rate_limited",
                started=started,
                http_status=429,
                latency_ms=latency_ms,
            )
        if resp.status_code == 422:
            return self._fail(
                request,
                status=ResearchFetchStatus.INVALID_URL,
                safe_error_code="invalid_url",
                started=started,
                http_status=422,
                latency_ms=latency_ms,
            )
        if resp.status_code in {401, 403}:
            return self._fail(
                request,
                status=ResearchFetchStatus.PROVIDER_UNAVAILABLE,
                safe_error_code="auth_error",
                started=started,
                http_status=resp.status_code,
                latency_ms=latency_ms,
            )
        if resp.status_code >= 500:
            return self._fail(
                request,
                status=ResearchFetchStatus.PROVIDER_UNAVAILABLE,
                safe_error_code="provider_unavailable",
                started=started,
                http_status=resp.status_code,
                latency_ms=latency_ms,
            )
        if resp.status_code != 200:
            return self._fail(
                request,
                status=ResearchFetchStatus.UNKNOWN_FAILURE,
                safe_error_code=f"http_{resp.status_code}",
                started=started,
                http_status=resp.status_code,
                latency_ms=latency_ms,
            )

        content = resp.text or ""
        if len(content.encode("utf-8", errors="ignore")) > request.max_content_bytes:
            content = content[: request.max_content_bytes]
        markdown = content.strip()
        if not markdown:
            return self._fail(
                request,
                status=ResearchFetchStatus.EMPTY_CONTENT,
                safe_error_code="empty_content",
                started=started,
                http_status=200,
                latency_ms=latency_ms,
            )
        title = _extract_title(markdown)
        content_hash = hashlib.sha256(markdown.encode("utf-8", errors="ignore")).hexdigest()
        attempt = int(request.trace_context.get("attempt_number", "1"))
        return FetchResult(
            provider=self.provider_name,
            source_url=request.source_url,
            final_url=url,
            normalized_url=request.normalized_url,
            fetched_at=utc_now(),
            status=ResearchFetchStatus.SUCCEEDED,
            http_status=200,
            content_type="text/markdown",
            title=title,
            raw_html=None,
            extracted_text=markdown,
            markdown=markdown,
            language=None,
            content_hash=content_hash,
            byte_count=len(markdown.encode("utf-8", errors="ignore")),
            latency_ms=latency_ms,
            attempt_number=attempt,
        )

    def _fail(
        self,
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
            provider=self.provider_name,
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


def _extract_title(markdown: str) -> str | None:
    for line in markdown.splitlines()[:20]:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()[:300] or None
    return None


async def probe_jina_reader(settings: Settings) -> dict[str, object]:
    import uuid

    adapter = JinaReaderFetchAdapter(settings)
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
        "latency_ms": result.latency_ms,
        "extracted_len": len(result.extracted_text),
        "safe_error_code": result.safe_error_code,
    }
