"""Direct HTTP fetch fallback — delegates to trafilatura contour."""

from __future__ import annotations

from typing import Any


async def direct_http_fetch(
    url: str,
    *,
    timeout_seconds: float = 25.0,
) -> tuple[int, str, str, str | None]:
    """Legacy shim — use LocalTrafilaturaFetchAdapter in orchestrator."""
    from uuid import uuid4

    from app.business_idea_validation.research_fetch.port import FetchRequest, ResearchFetchStatus
    from app.business_idea_validation.research_fetch.providers.trafilatura import (
        LocalTrafilaturaFetchAdapter,
    )
    from app.core.config import get_settings
    from app.db.base import utc_now

    settings = get_settings()
    adapter = LocalTrafilaturaFetchAdapter(settings)
    started = utc_now()
    req = FetchRequest(
        tenant_id=None,
        research_run_id=uuid4(),
        source_url=url,
        normalized_url=url,
        requested_at=started,
        timeout_seconds=timeout_seconds,
        max_content_bytes=settings.research_fetch_max_content_bytes,
    )
    result = await adapter.fetch(req)
    if result.status != ResearchFetchStatus.SUCCEEDED:
        return (
            result.http_status or 0,
            result.content_type or "",
            result.extracted_text,
            result.title,
        )
    return (
        result.http_status or 200,
        result.content_type or "text/html",
        result.extracted_text,
        result.title,
    )


async def probe_direct_http_fetch() -> dict[str, Any]:
    from app.business_idea_validation.research_fetch.providers.trafilatura import (
        probe_trafilatura_fetch,
    )
    from app.core.config import get_settings

    row = await probe_trafilatura_fetch(get_settings())
    row["provider"] = "direct_http"
    return row
