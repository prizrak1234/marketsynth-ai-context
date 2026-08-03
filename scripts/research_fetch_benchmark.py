#!/usr/bin/env python3
"""Benchmark-only extraction comparison — not wired to production runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.core.config import get_settings


async def _run(urls: list[str]) -> dict[str, object]:
    settings = get_settings()
    rows: list[dict[str, object]] = []
    for url in urls:
        row: dict[str, object] = {"url": url}
        try:
            from app.business_idea_validation.research_fetch.providers.trafilatura import (
                LocalTrafilaturaFetchAdapter,
            )
            from app.business_idea_validation.research_fetch.port import FetchRequest
            from uuid import uuid4
            from app.db.base import utc_now

            req = FetchRequest(
                tenant_id=None,
                research_run_id=uuid4(),
                source_url=url,
                normalized_url=url,
                requested_at=utc_now(),
                timeout_seconds=settings.research_fetch_timeout_seconds,
                max_content_bytes=settings.research_fetch_max_content_bytes,
            )
            traf = await LocalTrafilaturaFetchAdapter(settings).fetch(req)
            row["trafilatura"] = {
                "status": traf.status.value,
                "len": len(traf.extracted_text),
                "latency_ms": traf.latency_ms,
            }
        except Exception as exc:  # noqa: BLE001
            row["trafilatura"] = {"error": type(exc).__name__}
        rows.append(row)
    return {
        "urls": len(urls),
        "results": rows,
        "recommendation": {
            "runtime_order": settings.research_fetch_provider_order,
            "playwright_enabled": settings.research_fetch_playwright_enabled,
            "newspaper3k": "benchmark_only_not_in_runtime_v1",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Research fetch extraction benchmark (read-only)")
    parser.add_argument("--urls-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("docs/research_fetch_benchmark_report.json"))
    args = parser.parse_args()
    urls = [line.strip() for line in args.urls_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = asyncio.run(_run(urls[:10]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"written": str(args.out), "urls": report["urls"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
