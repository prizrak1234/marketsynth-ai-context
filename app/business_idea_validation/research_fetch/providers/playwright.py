"""Playwright + Readability fallback — disabled by default (v1)."""

from __future__ import annotations

from app.business_idea_validation.research_fetch.port import (
    FetchRequest,
    FetchResult,
    ResearchFetchStatus,
)
from app.business_tools.contracts import BusinessToolError
from app.core.config import Settings
from app.db.base import utc_now


class PlaywrightReadabilityFetchAdapter:
    provider_name = "playwright"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_available(self) -> bool:
        return bool(self._settings.research_fetch_playwright_enabled)

    async def fetch(self, request: FetchRequest) -> FetchResult:
        if not self.is_available():
            raise BusinessToolError("not_configured", "Playwright fetch is disabled.")
        started = utc_now()
        attempt = int(request.trace_context.get("attempt_number", "1"))
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise BusinessToolError("not_configured", "Playwright is not installed.") from exc

        url = request.normalized_url
        timeout_ms = int(request.timeout_seconds * 1000)
        text = ""
        title: str | None = None
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(
                        java_script_enabled=True,
                        accept_downloads=False,
                        ignore_https_errors=False,
                    )
                    page = await context.new_page()
                    await page.route("**/*", _block_private_routes)
                    await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                    html = await page.content()
                    title = await page.title()
                    inner_text = await page.evaluate("document.body.innerText")
                    text = _readability_extract(html, url) or inner_text
                finally:
                    await browser.close()
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((utc_now() - started).total_seconds() * 1000)
            code = "timeout" if "timeout" in str(exc).lower() else "provider_unavailable"
            fail_status = (
                ResearchFetchStatus.TIMEOUT
                if code == "timeout"
                else ResearchFetchStatus.PROVIDER_UNAVAILABLE
            )
            return FetchResult(
                provider=self.provider_name,
                source_url=request.source_url,
                final_url=url,
                normalized_url=request.normalized_url,
                fetched_at=utc_now(),
                status=fail_status,
                http_status=None,
                content_type="text/html",
                title=title,
                raw_html=None,
                extracted_text="",
                markdown=None,
                language=None,
                content_hash="",
                byte_count=0,
                latency_ms=latency_ms,
                attempt_number=attempt,
                safe_error_code=code,
            )

        import hashlib

        text = (text or "").strip()
        if not text:
            latency_ms = int((utc_now() - started).total_seconds() * 1000)
            return FetchResult(
                provider=self.provider_name,
                source_url=request.source_url,
                final_url=url,
                normalized_url=request.normalized_url,
                fetched_at=utc_now(),
                status=ResearchFetchStatus.EMPTY_CONTENT,
                http_status=200,
                content_type="text/html",
                title=title,
                raw_html=None,
                extracted_text="",
                markdown=None,
                language=None,
                content_hash="",
                byte_count=0,
                latency_ms=latency_ms,
                attempt_number=attempt,
                safe_error_code="empty_content",
            )
        content_hash = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        latency_ms = int((utc_now() - started).total_seconds() * 1000)
        return FetchResult(
            provider=self.provider_name,
            source_url=request.source_url,
            final_url=url,
            normalized_url=request.normalized_url,
            fetched_at=utc_now(),
            status=ResearchFetchStatus.SUCCEEDED,
            http_status=200,
            content_type="text/html",
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


async def _block_private_routes(route, request) -> None:  # noqa: ANN001
    from app.business_idea_validation.research_fetch.security import validate_fetch_url

    url = request.url
    safe, _ = validate_fetch_url(url)
    if not safe:
        await route.abort("blockedbyclient")
        return
    await route.continue_()


def _readability_extract(html: str, url: str) -> str | None:
    try:
        from readability import Document

        doc = Document(html)
        summary_html = doc.summary()
        from app.business_idea_validation.research_fetch.providers.trafilatura import (
            _regex_fallback,
        )

        _, text = _regex_fallback(summary_html)
        return text if text.strip() else None
    except ImportError:
        return None
    except Exception:  # noqa: BLE001
        return None
