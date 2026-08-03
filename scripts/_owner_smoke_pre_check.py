#!/usr/bin/env python3
"""Read-only pre-smoke baseline for RUNTIME-01G owner real research smoke."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory


async def _db_baseline() -> dict:
    factory = get_session_factory()
    async with factory() as session:
        active = (
            await session.execute(
                text(
                    """
                    SELECT id, project_id, user_request_id, status, created_at
                    FROM business_idea_validation_runs
                    WHERE status IN ('queued', 'running')
                    ORDER BY created_at DESC
                    """
                )
            )
        ).mappings().all()
        violations = (
            await session.execute(
                text(
                    """
                    SELECT project_id, COUNT(*) AS active_count
                    FROM business_idea_validation_runs
                    WHERE status IN ('queued', 'running')
                    GROUP BY project_id
                    HAVING COUNT(*) > 1
                    """
                )
            )
        ).mappings().all()
        recent = (
            await session.execute(
                text(
                    """
                    SELECT id, project_id, status, created_at, finished_at
                    FROM business_idea_validation_runs
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                )
            )
        ).mappings().all()
    return {
        "active_runs": [dict(r) for r in active],
        "active_run_count_global": len(active),
        "constraint_violations": [dict(v) for v in violations],
        "recent_runs": [dict(r) for r in recent],
    }


def _settings_snapshot() -> dict:
    s = get_settings()
    return {
        "app_env": s.app_env,
        "business_idea_validation_enabled": s.business_idea_validation_enabled,
        "biv_run_dispatcher_enabled": s.biv_run_dispatcher_enabled,
        "biv_e2e_deterministic_enabled": s.biv_e2e_deterministic_enabled,
        "research_source_collection_enabled": s.research_source_collection_enabled,
        "research_source_collection_mock_providers": s.research_source_collection_mock_providers,
        "fetch_contour_operational_providers": list(
            getattr(s, "biv_fetch_operational_providers", []) or []
        )
        if hasattr(s, "biv_fetch_operational_providers")
        else None,
    }


def main() -> int:
    settings = _settings_snapshot()
    db = asyncio.run(_db_baseline())
    try:
        alembic = subprocess.run(
            ["uv", "run", "alembic", "current"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(__file__).replace("scripts\\_owner_smoke_pre_check.py", "").rstrip("\\"),
        )
        alembic_current = (alembic.stdout or alembic.stderr or "").strip()
    except Exception as exc:  # noqa: BLE001
        alembic_current = f"error: {exc}"

    blocked_reasons: list[str] = []
    if settings["biv_e2e_deterministic_enabled"]:
        blocked_reasons.append("BIV_E2E_DETERMINISTIC_ENABLED=true (must be false for real smoke)")
    if settings["research_source_collection_mock_providers"]:
        blocked_reasons.append("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS=true")
    if not settings["biv_run_dispatcher_enabled"]:
        blocked_reasons.append("BIV_RUN_DISPATCHER_ENABLED=false")
    if db["active_run_count_global"] > 0:
        blocked_reasons.append(
            f"global active BIV runs={db['active_run_count_global']} — resolve before new smoke"
        )
    if db["constraint_violations"]:
        blocked_reasons.append("partial unique index violations in DB")

    payload = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "pre_smoke_verdict": "BLOCKED" if blocked_reasons else "READY",
        "blocked_reasons": blocked_reasons,
        "settings": settings,
        "alembic_current": alembic_current,
        "database": db,
    }
    print(json.dumps(payload, indent=2, default=str))
    return 1 if blocked_reasons else 0


if __name__ == "__main__":
    sys.exit(main())
