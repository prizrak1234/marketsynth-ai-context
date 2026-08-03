"""Verify alembic head 20260730_0065 and partial unique index (RUNTIME-01G)."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys

from app.db.session import get_session_factory
from sqlalchemy import text


def _alembic_current() -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return proc.stdout.strip()


async def _verify() -> dict:
    current = _alembic_current()
    head_ok = "20260730_0065" in current

    factory = get_session_factory()
    async with factory() as session:
        bind = session.get_bind()
        dialect = bind.dialect.name if bind is not None else "unknown"

        index_row = None
        if dialect == "postgresql":
            index_row = (
                await session.execute(
                    text(
                        """
                        SELECT indexdef
                        FROM pg_indexes
                        WHERE indexname = 'uq_biv_one_active_run_per_project'
                        """
                    )
                )
            ).scalar_one_or_none()
        elif dialect == "sqlite":
            index_row = (
                await session.execute(
                    text(
                        """
                        SELECT sql
                        FROM sqlite_master
                        WHERE type = 'index' AND name = 'uq_biv_one_active_run_per_project'
                        """
                    )
                )
            ).scalar_one_or_none()

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
        ).all()

    index_text = str(index_row) if index_row else ""
    condition_ok = index_row is not None and "queued" in index_text and "running" in index_text
    return {
        "alembic_current": current,
        "head_ok": head_ok,
        "dialect": dialect,
        "index_exists": index_row is not None,
        "partial_condition_ok": condition_ok,
        "index_definition": str(index_row) if index_row else None,
        "data_violations": [
            {"project_id": str(v[0]), "active_count": int(v[1])} for v in violations
        ],
        "ok": head_ok and index_row is not None and condition_ok and len(violations) == 0,
    }


def main() -> int:
    result = asyncio.run(_verify())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
