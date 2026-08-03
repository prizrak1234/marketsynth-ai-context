#!/usr/bin/env python3
"""Constrained multi-provider fetch smoke — max 6 public URLs, no research run."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.business_idea_validation.fetch_orchestrator import BivFetchOrchestrator
from app.business_idea_validation.pipeline_metrics import BivPipelineMetricsRecorder
from app.core.config import get_settings
from app.db.session import get_session_factory


@dataclass
class UrlSmokeRow:
    label: str
    source_url: str
    normalized_url: str = ""
    success: bool = False
    provider: str | None = None
    fallback_used: bool = False
    latency_ms: int | None = None
    title: str | None = None
    char_count: int = 0
    content_hash: str = ""
    outcome: str = ""
    attempt_lineage: list[dict[str, object]] = field(default_factory=list)
    quality_verdict: str = ""
    duplicate_second_fetch: bool | None = None
    error: str | None = None


DEFAULT_URLS: list[tuple[str, str]] = [
    ("ru_static", "https://ru.wikipedia.org/wiki/Маркетинг"),
    ("en_static", "https://en.wikipedia.org/wiki/Market_research"),
    ("js_heavy", "https://example.com/"),
    ("redirect", "https://www.wikipedia.org/"),
    ("unavailable", "https://example.com/this-page-does-not-exist-404"),
    ("duplicate", "https://en.wikipedia.org/wiki/Market_research"),
]


def _quality_verdict(*, title: str | None, text: str, label: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return "fail_empty"
    if len(cleaned) < 400:
        return "fail_too_short"
    boilerplate_markers = ("cookie", "navigation", "skip to", "javascript")
    lower = cleaned.lower()
    hits = sum(1 for m in boilerplate_markers if m in lower[:500])
    if hits >= 3 and len(cleaned) < 800:
        return "fail_boilerplate"
    if title or label in {"unavailable", "redirect"}:
        return "pass"
    if not title and len(cleaned) >= 400:
        return "pass_no_title"
    return "pass"


async def _smoke_url(
    orchestrator: BivFetchOrchestrator,
    label: str,
    url: str,
    *,
    check_duplicate: bool = False,
) -> UrlSmokeRow:
    row = UrlSmokeRow(label=label, source_url=url)
    try:
        result = await orchestrator.fetch_url(url, query_id=f"smoke-{label}")
        row.normalized_url = result.normalized_url
        row.success = result.success
        row.provider = result.provider
        row.fallback_used = result.fallback_used
        row.outcome = result.outcome.value
        row.title = result.title
        text = result.extracted_text or ""
        row.char_count = len(text)
        row.content_hash = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
        row.attempt_lineage = [
            {
                "provider": item.provider,
                "status": item.status.value,
                "safe_error_code": item.safe_error_code,
                "latency_ms": item.latency_ms,
            }
            for item in result.attempt_lineage
        ]
        row.quality_verdict = _quality_verdict(title=row.title, text=text, label=label)
        if check_duplicate:
            second = await orchestrator.fetch_url(url, query_id=f"smoke-{label}-dup")
            row.duplicate_second_fetch = (
                second.outcome.value == "duplicate_url"
                or (
                    second.success
                    and second.extracted_text == (result.extracted_text if result.success else "")
                )
            )
    except Exception as exc:  # noqa: BLE001
        row.error = type(exc).__name__
        row.quality_verdict = "fail_exception"
        raise
    return row


async def run_smoke(urls: list[tuple[str, str]]) -> dict[str, object]:
    from app.db.repositories import biv_fetch_ledger as ledger_mod

    settings = get_settings()
    metrics = BivPipelineMetricsRecorder()
    factory = get_session_factory()
    run_id = uuid4()

    async def _ledger_noop(self, row):  # noqa: ANN001
        row.id = uuid4()
        return row

    original_append = ledger_mod.BivFetchLedgerRepository.append
    ledger_mod.BivFetchLedgerRepository.append = _ledger_noop  # type: ignore[method-assign]
    rows: list[UrlSmokeRow] = []
    async with factory() as session:
        orchestrator = BivFetchOrchestrator(
            session,
            settings,
            run_id=run_id,
            correlation_id="fetch-smoke",
            metrics=metrics,
        )
        seen: set[str] = set()
        for label, url in urls[:6]:
            is_dup = label == "duplicate" or url in seen
            seen.add(url)
            try:
                rows.append(
                    await _smoke_url(
                        orchestrator,
                        label,
                        url,
                        check_duplicate=is_dup,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                await session.rollback()
                rows.append(
                    UrlSmokeRow(
                        label=label,
                        source_url=url,
                        error=type(exc).__name__,
                        quality_verdict="fail_exception",
                    )
                )

    ledger_mod.BivFetchLedgerRepository.append = original_append  # type: ignore[method-assign]

    m = metrics.data.fetch
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": str(run_id),
        "provider_order": settings.research_fetch_provider_order,
        "results": [asdict(r) for r in rows],
        "budget": {
            "fetch_attempts": m.fetch_attempts,
            "fetch_success_count": m.fetch_success_count,
            "fetch_failure_count": m.fetch_failure_count,
            "fallback_success_count": m.fallback_success_count,
            "duplicate_url_skipped_total": m.duplicate_url_skipped_total,
            "cache_hit_total": m.cache_hit_total,
            "fetch_attempts_by_provider": dict(m.fetch_attempts_by_provider),
            "fetch_success_by_provider": dict(m.fetch_success_by_provider),
            "all_providers_failed_total": m.all_providers_failed_total,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Constrained fetch smoke (max 6 URLs)")
    parser.add_argument("--out", type=Path, default=Path("docs/research_fetch_smoke_report.json"))
    args = parser.parse_args()
    report = asyncio.run(run_smoke(DEFAULT_URLS))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"written": str(args.out), "urls": len(report["results"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
