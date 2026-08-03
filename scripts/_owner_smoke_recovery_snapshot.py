#!/usr/bin/env python3
"""Read-only stale-run recovery snapshot for owner smoke env reset."""

from __future__ import annotations

import asyncio
import json
import sys
from uuid import UUID

from sqlalchemy import text

from app.db.session import get_session_factory

RUN_ID = UUID("2ed57784-a4f4-48d6-b81d-128f8589ac92")
PROJECT_ID = UUID("c9737da3-b1d1-49d4-a2e2-ba9c95270f1e")


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        run = (
            await session.execute(
                text(
                    """
                    SELECT id, project_id, status, error_code, safe_error_message,
                           finished_at, progress_json, investigation_id
                    FROM business_idea_validation_runs WHERE id = :rid
                    """
                ),
                {"rid": RUN_ID},
            )
        ).mappings().first()
        inv = (
            await session.execute(
                text("SELECT id, status FROM investigations WHERE id = :iid"),
                {"iid": run["investigation_id"]},
            )
        ).mappings().first() if run else None
        active_project = (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM business_idea_validation_runs
                    WHERE project_id = :pid AND status IN ('queued', 'running')
                    """
                ),
                {"pid": PROJECT_ID},
            )
        ).scalar()
        active_global = (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM business_idea_validation_runs
                    WHERE status IN ('queued', 'running')
                    """
                )
            )
        ).scalar()
    print(
        json.dumps(
            {
                "run": dict(run) if run else None,
                "investigation": dict(inv) if inv else None,
                "active_runs_project": int(active_project or 0),
                "active_runs_global": int(active_global or 0),
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
