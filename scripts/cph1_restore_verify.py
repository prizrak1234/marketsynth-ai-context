"""One-off restore verification helper for CPH.1 (disposable DB only)."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.cph1_db_tools import assert_disposable, to_dsn  # noqa: E402


async def main() -> int:
    target = os.environ.get("RESTORE_DB", "botfazer_cph1_restore")
    assert_disposable(target)
    backup = Path(
        os.environ.get(
            "BACKUP_SQL",
            str(Path.home() / "botfazer_backups" / "backup_botfazer_20260715T164718Z.sql"),
        )
    )
    if not backup.is_file():
        print("missing_backup=", backup)
        return 2

    super_dsn = os.environ.get(
        "SUPERUSER_DATABASE_URL",
        "postgresql://postgres:botfazer@localhost:5432/postgres",
    )
    # never print credentials
    print("target_db=", target)
    print("backup=", backup.name)

    conn = await asyncpg.connect(super_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=$1 AND pid <> pg_backend_pid()",
            target,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{target}"')
        await conn.execute(f'CREATE DATABASE "{target}" OWNER botfazer')
    finally:
        await conn.close()

    psql = Path(r"C:\Program Files\PostgreSQL\17\bin\psql.exe")
    env = os.environ.copy()
    if "PGPASSWORD" not in env:
        env["PGPASSWORD"] = "botfazer"
    proc = subprocess.run(
        [
            str(psql),
            "-h",
            "localhost",
            "-U",
            "botfazer",
            "-d",
            target,
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(backup),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("restore_failed=", (proc.stderr or proc.stdout)[:500])
        return 3
    print("restore_ok=True")

    vconn = await asyncpg.connect(f"postgresql://botfazer:botfazer@localhost:5432/{target}")
    try:
        rev = await vconn.fetchval("select version_num from alembic_version")
        has_learn = await vconn.fetchval(
            "select exists(select 1 from information_schema.tables "
            "where table_schema='public' and table_name='campaign_learnings')"
        )
        has_brief = await vconn.fetchval(
            "select exists(select 1 from information_schema.tables "
            "where table_schema='public' and table_name='project_briefs')"
        )
        print("alembic_revision=", rev)
        print("has_campaign_learnings=", has_learn)
        print("has_project_briefs=", has_brief)
        print("restore_verification=", "ok" if rev == "20260608_0033" and has_learn else "mismatch")
    finally:
        await vconn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
