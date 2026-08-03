#!/usr/bin/env python
"""PRODUCT-01.3A.2 — repair SQLite dev database for BIV intake gate.

SQLite Alembic chains may fail on legacy FK migrations. For local development,
this script bootstraps schema via SQLModel metadata and stamps Alembic head.

Usage:
  uv run python scripts/repair_product_01_3a_dev_db.py
  uv run python scripts/repair_product_01_3a_dev_db.py --fresh

PostgreSQL owners should use:
  uv run alembic upgrade head
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import SQLModel

from app.core.config import get_settings
from app.db.session import close_db, get_engine, init_db, reset_db_state
from app.domain.alembic_revision_guard import is_revision_in_chain, list_code_revisions
from app.services.analysis_context_subsystem_readiness import inspect_analysis_context_subsystem

# Minimum migration that introduced analysis_contexts — not the code head.
PRODUCT_01_3A_MIN_REVISION = "20260724_0060"


def _sqlite_path(database_url: str) -> Path | None:
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if database_url.startswith(prefix):
            raw = database_url[len(prefix) :]
            path = Path(raw)
            if not path.is_absolute():
                path = (ROOT / path).resolve()
            return path
    return None


def _code_head() -> str:
    code_map = list_code_revisions()
    downs = {d for d in code_map.values() if d}
    heads = sorted(r for r in code_map if r not in downs)
    if len(heads) != 1:
        raise SystemExit(f"expected_single_alembic_head got={heads}")
    return heads[0]


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "alembic", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


async def _readiness() -> dict:
    engine = get_engine()
    status = await inspect_analysis_context_subsystem(engine)
    return status.as_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair SQLite dev DB for PRODUCT-01.3A")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete SQLite file and recreate schema from ORM metadata",
    )
    args = parser.parse_args()

    settings = get_settings()
    url = settings.database_url
    scheme = urlparse(url.replace("+asyncpg", "")).scheme
    if "sqlite" not in scheme:
        print(
            json.dumps(
                {
                    "status": "refused",
                    "detail": "sqlite_only_use_alembic_upgrade_head_for_postgresql",
                    "database_scheme": scheme,
                },
                indent=2,
            )
        )
        return 2

    db_path = _sqlite_path(url)
    head = _code_head()
    min_revision_ok = is_revision_in_chain(PRODUCT_01_3A_MIN_REVISION, head=head)

    if args.fresh and db_path is not None and db_path.is_file():
        db_path.unlink()

    before = asyncio.run(_bootstrap_readiness(create=True))
    stamp = _run_alembic("stamp", head)
    if stamp.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "phase": "alembic_stamp",
                    "stderr": (stamp.stderr or "")[-2000:],
                    "stdout": (stamp.stdout or "")[-2000:],
                },
                indent=2,
            )
        )
        return 1

    after = asyncio.run(_bootstrap_readiness(create=False))
    ok = after.get("ready") is True and min_revision_ok
    print(
        json.dumps(
            {
                "status": "passed" if ok else "failed",
                "database_path": str(db_path) if db_path else None,
                "stamped_revision": head,
                "code_head": head,
                "required_min_revision": PRODUCT_01_3A_MIN_REVISION,
                "required_min_revision_in_chain": min_revision_ok,
                "before": before,
                "after": after,
                "next_steps": [
                    "uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000",
                    "open http://127.0.0.1:8000/openapi.json",
                    "retry PRODUCT-01.3A smoke",
                ],
            },
            indent=2,
        )
    )
    return 0 if ok else 1


async def _bootstrap_readiness(*, create: bool) -> dict:
    reset_db_state()
    await init_db()
    if create:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    try:
        return await _readiness()
    finally:
        await close_db()


if __name__ == "__main__":
    raise SystemExit(main())
