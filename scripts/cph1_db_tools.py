"""CPH.1 scripts: disposable DB, backup metadata, revision check, bootstrap.

Never auto-stamps. Never targets production without explicit DB name checks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.domain.alembic_revision_guard import classify_revision, list_code_revisions


SAFE_DISPOSABLE_DBS = frozenset(
    {
        "botfazer_cph1",
        "botfazer_pilot",
        "botfazer_migtest",
        "botfazer_test",
    }
)
FORBIDDEN_TARGETS = frozenset({"botfazer", "postgres", "template0", "template1"})


def safe_url(url: str) -> str:
    return re.sub(r"://([^:/]+):([^@]+)@", r"://\1:***@", url)


def to_dsn(url: str) -> str:
    for p in (
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
        "postgresql+psycopg2://",
    ):
        if url.startswith(p):
            return "postgresql://" + url[len(p) :]
    return url


def parse_db_name(url: str) -> str:
    u = urlparse(to_dsn(url))
    return (u.path or "").lstrip("/")


def admin_dsn(url: str) -> str:
    """Connect to maintenance DB `postgres` on same host."""
    dsn = to_dsn(url)
    u = urlparse(dsn)
    return f"{u.scheme}://{u.netloc}/postgres"


def replace_db(url: str, db_name: str) -> str:
    dsn = to_dsn(url)
    u = urlparse(dsn)
    return f"{u.scheme}://{u.netloc}/{db_name}"


def assert_disposable(db_name: str) -> None:
    if db_name in FORBIDDEN_TARGETS:
        raise SystemExit(
            f"refused: database '{db_name}' is not a disposable CPH target "
            f"(forbidden={sorted(FORBIDDEN_TARGETS)})"
        )
    if db_name not in SAFE_DISPOSABLE_DBS and not db_name.startswith("botfazer_cph"):
        raise SystemExit(
            f"refused: '{db_name}' is not an approved disposable name. "
            f"Use one of {sorted(SAFE_DISPOSABLE_DBS)} or botfazer_cph*."
        )


async def cmd_check_revision() -> int:
    import asyncpg

    settings = get_settings()
    print("database_url_safe=", safe_url(settings.database_url))
    code_map = list_code_revisions()
    downs = {d for d in code_map.values() if d}
    heads = sorted(r for r in code_map if r not in downs)
    print("code_heads=", heads)

    conn = await asyncpg.connect(to_dsn(settings.database_url))
    try:
        has = await conn.fetchval(
            "select exists(select 1 from information_schema.tables "
            "where table_schema='public' and table_name='alembic_version')"
        )
        revs: list[str] = []
        if has:
            rows = await conn.fetch("select version_num from alembic_version")
            revs = [r["version_num"] for r in rows]
        diag = classify_revision(database_revisions=revs, code_heads=heads, code_revisions=code_map)
        print("database_revisions=", list(diag.database_revisions))
        print("state=", diag.state.value)
        print("detail=", diag.detail)
        print("auto_stamp_allowed=", diag.auto_stamp_allowed)
        print("auto_migrate_allowed=", diag.auto_migrate_allowed)
        return 0 if diag.state.value in {"current", "behind", "empty"} else 3
    finally:
        await conn.close()


async def cmd_create_disposable(db_name: str) -> int:
    import asyncpg

    assert_disposable(db_name)
    settings = get_settings()
    print("creating_disposable=", db_name)
    print("admin_url_safe=", safe_url(admin_dsn(settings.database_url)))
    conn = await asyncpg.connect(admin_dsn(settings.database_url))
    try:
        exists = await conn.fetchval("select 1 from pg_database where datname=$1", db_name)
        if exists:
            print("already_exists=", True)
        else:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print("created=", True)
    finally:
        await conn.close()
    print("target_url_hint=", safe_url(replace_db(settings.database_url, db_name)))
    return 0


async def cmd_drop_disposable(db_name: str) -> int:
    import asyncpg

    assert_disposable(db_name)
    settings = get_settings()
    conn = await asyncpg.connect(admin_dsn(settings.database_url))
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=$1 AND pid <> pg_backend_pid()",
            db_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        print("dropped=", db_name)
    finally:
        await conn.close()
    return 0


async def cmd_backup(out_dir: Path) -> int:
    """Logical backup: prefer pg_dump; else asyncpg schema+count metadata JSON."""
    import asyncpg

    settings = get_settings()
    db_name = parse_db_name(settings.database_url)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta_path = out_dir / f"backup_meta_{db_name}_{stamp}.json"
    dump_path = out_dir / f"backup_{db_name}_{stamp}.sql"

    conn = await asyncpg.connect(to_dsn(settings.database_url))
    try:
        revs = []
        if await conn.fetchval(
            "select exists(select 1 from information_schema.tables "
            "where table_name='alembic_version')"
        ):
            revs = [
                r["version_num"]
                for r in await conn.fetch("select version_num from alembic_version")
            ]
        tables = [
            r["table_name"]
            for r in await conn.fetch(
                "select table_name from information_schema.tables "
                "where table_schema='public' and table_type='BASE TABLE' order by 1"
            )
        ]
        counts = {}
        for t in tables:
            counts[t] = await conn.fetchval(f'select count(*) from "{t}"')
        ver = await conn.fetchval("select version()")
        size = await conn.fetchval(
            "select pg_size_pretty(pg_database_size(current_database()))"
        )
    finally:
        await conn.close()

    dump_ok = False
    dump_tool = None
    # Try common Windows PostgreSQL install paths
    candidates = [
        Path(r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"),
        Path(r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"),
        Path(r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"),
    ]
    which = None
    for c in candidates:
        if c.exists():
            which = c
            break
    if which is None:
        from shutil import which as sh_which

        w = sh_which("pg_dump")
        if w:
            which = Path(w)

    if which is not None:
        dump_tool = str(which)
        # Use env var PGPASSWORD only in subprocess env if present; do not print.
        env = os.environ.copy()
        dsn = to_dsn(settings.database_url)
        u = urlparse(dsn)
        if u.password and "PGPASSWORD" not in env:
            env["PGPASSWORD"] = u.password
        cmd = [
            str(which),
            "-h",
            u.hostname or "localhost",
            "-p",
            str(u.port or 5432),
            "-U",
            u.username or "postgres",
            "-d",
            db_name,
            "-F",
            "p",
            "-f",
            str(dump_path),
        ]
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
        dump_ok = proc.returncode == 0
        if not dump_ok:
            print("pg_dump_error=", (proc.stderr or proc.stdout)[:400])

    meta = {
        "timestamp_utc": stamp,
        "database": db_name,
        "alembic_revisions": revs,
        "pg_version": str(ver).split(",")[0][:120],
        "db_size": size,
        "table_count": len(tables),
        "row_counts": counts,
        "dump_file": dump_path.name if dump_ok else None,
        "dump_tool": dump_tool,
        "dump_ok": dump_ok,
        "note": (
            "Metadata always written. Full SQL dump only when pg_dump succeeds. "
            "Store backups outside the git repo."
        ),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print("backup_meta=", str(meta_path))
    print("dump_ok=", dump_ok)
    print("alembic_revisions=", revs)
    return 0 if (dump_ok or meta_path.exists()) else 1


async def cmd_schema_parity() -> int:
    """Check commercial MVP tables exist for current DATABASE_URL."""
    import asyncpg

    from scripts.cph1_inventory_postgresql import COMMERCIAL

    settings = get_settings()
    conn = await asyncpg.connect(to_dsn(settings.database_url))
    try:
        missing = []
        present = []
        for t in COMMERCIAL:
            ok = await conn.fetchval(
                "select exists(select 1 from information_schema.tables "
                "where table_schema='public' and table_name=$1)",
                t,
            )
            if ok:
                present.append(t)
            else:
                missing.append(t)
        print("present=", present)
        print("missing=", missing)
        return 0 if not missing else 4
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="CPH.1 database tooling")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check-revision")
    p_create = sub.add_parser("create-disposable")
    p_create.add_argument("--db", default="botfazer_cph1")
    p_drop = sub.add_parser("drop-disposable")
    p_drop.add_argument("--db", default="botfazer_cph1")
    p_backup = sub.add_parser("backup")
    p_backup.add_argument(
        "--out",
        default=str(Path.home() / "botfazer_backups"),
        help="Directory outside the git repo",
    )
    sub.add_parser("schema-parity")

    args = parser.parse_args()
    if args.cmd == "check-revision":
        return asyncio.run(cmd_check_revision())
    if args.cmd == "create-disposable":
        return asyncio.run(cmd_create_disposable(args.db))
    if args.cmd == "drop-disposable":
        return asyncio.run(cmd_drop_disposable(args.db))
    if args.cmd == "backup":
        return asyncio.run(cmd_backup(Path(args.out)))
    if args.cmd == "schema-parity":
        return asyncio.run(cmd_schema_parity())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
