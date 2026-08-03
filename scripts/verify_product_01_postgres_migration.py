#!/usr/bin/env python
"""Verify PRODUCT-01 Alembic migration on PostgreSQL (PRODUCT-01.2 A1).

Usage (owner / CI with isolated PostgreSQL):

  export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/marketsynth_migrate_test"
  uv run python scripts/verify_product_01_postgres_migration.py

Requires empty or disposable database. Runs `alembic upgrade head`, verifies
PRODUCT-01 tables/constraints, optionally `alembic downgrade -1` when
PRODUCT_01_VERIFY_DOWNGRADE=true.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

PRODUCT_01_REVISION = "20260724_0059"
PRODUCT_01_TABLES = (
    "commercial_upstream_snapshots",
    "offer_artifacts",
    "offer_artifact_versions",
    "offer_review_events",
)
EXPECTED_UNIQUE = {
    "offer_artifacts": {
        "uq_offer_launch_pack",
        "uq_offer_owner_idempotency",
    },
    "offer_artifact_versions": {"uq_offer_version_number"},
    "offer_review_events": {"uq_offer_review_version_decision"},
    "commercial_upstream_snapshots": {"uq_upstream_launch_artifact_type"},
}
BRIDGE_COLUMNS = (
    "source_mode",
    "bridge_version",
    "source_biv_id",
    "source_biv_hash",
    "generated_from_fields",
    "limitations",
    "replacement_required",
)


def _require_postgres_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print(json.dumps({"error": "DATABASE_URL_required"}))
        sys.exit(1)
    if "postgresql" not in url and "postgres" not in url:
        print(json.dumps({"error": "postgresql_required", "got": url.split("://")[0]}))
        sys.exit(1)
    return url


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    return subprocess.run(
        ["uv", "run", "alembic", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


async def _inspect_db(url: str) -> dict:
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        def _sync_inspect(sync_conn):  # noqa: ANN001
            return inspect(sync_conn)

        inspector = await conn.run_sync(_sync_inspect)
        tables = set(inspector.get_table_names())
        report: dict = {"tables_present": {}, "indexes": {}, "uniques": {}, "columns": {}}
        for table in PRODUCT_01_TABLES:
            report["tables_present"][table] = table in tables
            if table not in tables:
                continue
            report["indexes"][table] = [idx["name"] for idx in inspector.get_indexes(table)]
            uniques = {u["name"] for u in inspector.get_unique_constraints(table)}
            report["uniques"][table] = sorted(uniques)
            report["columns"][table] = [
                col["name"] for col in inspector.get_columns(table)
            ]
        rev = await conn.execute(text("SELECT version_num FROM alembic_version"))
        row = rev.fetchone()
        report["alembic_version"] = row[0] if row else None
    await engine.dispose()
    return report


def main() -> int:
    url = _require_postgres_url()
    started = time.monotonic()
    before = _run_alembic("current")
    start_rev = (before.stdout or before.stderr or "").strip()

    upgrade = _run_alembic("upgrade", "head")
    if upgrade.returncode != 0:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "phase": "upgrade_head",
                    "returncode": upgrade.returncode,
                    "stderr": upgrade.stderr[-4000:],
                    "stdout": upgrade.stdout[-4000:],
                },
                indent=2,
            )
        )
        return 1

    inspection = asyncio.run(_inspect_db(url))
    duration_s = round(time.monotonic() - started, 2)

    missing_tables = [t for t in PRODUCT_01_TABLES if not inspection["tables_present"].get(t)]
    missing_uniques: list[str] = []
    for table, names in EXPECTED_UNIQUE.items():
        present = set(inspection["uniques"].get(table, []))
        for name in names:
            if name not in present:
                missing_uniques.append(f"{table}.{name}")

    bridge_missing = [
        col
        for col in BRIDGE_COLUMNS
        if col not in inspection["columns"].get("commercial_upstream_snapshots", [])
    ]

    downgrade_ok: bool | None = None
    if os.environ.get("PRODUCT_01_VERIFY_DOWNGRADE", "").lower() in {"1", "true", "yes"}:
        down = _run_alembic("downgrade", "-1")
        downgrade_ok = down.returncode == 0
        if downgrade_ok:
            _run_alembic("upgrade", "head")

    ok = (
        not missing_tables
        and not missing_uniques
        and not bridge_missing
        and inspection.get("alembic_version") == PRODUCT_01_REVISION
    )

    report = {
        "status": "passed" if ok else "failed",
        "captured_at": datetime.now(UTC).isoformat(),
        "postgresql_url_scheme": url.split("://")[0],
        "starting_revision_hint": start_rev,
        "final_revision": inspection.get("alembic_version"),
        "expected_revision": PRODUCT_01_REVISION,
        "duration_seconds": duration_s,
        "missing_tables": missing_tables,
        "missing_unique_constraints": missing_uniques,
        "missing_bridge_columns": bridge_missing,
        "inspection": inspection,
        "downgrade_one_step_ok": downgrade_ok,
        "upgrade_stdout_tail": (upgrade.stdout or "")[-2000:],
        "warnings": [],
    }
    if downgrade_ok is False:
        report["warnings"].append("downgrade -1 failed — check project downgrade policy")

    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
