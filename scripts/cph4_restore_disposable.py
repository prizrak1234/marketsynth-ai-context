"""CPH.4 — restore verified backup into disposable botfazer_cph4_restore_* DB."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from scripts.cph4_common import (
    EXPECTED_REVISION,
    PROTECTED_SOURCE_DBS,
    Cph4Error,
    admin_dsn,
    assert_restore_target,
    find_pg_bin,
    now_iso,
    parse_db_name,
    replace_db,
    require_owner_approval,
    run_pg,
    safe_url,
    to_dsn,
)
from scripts.cph4_verify_backup import verify_backup


def _superuser_admin_dsn(settings_url: str) -> str:
    """Prefer SUPERUSER_DATABASE_URL for CREATE/DROP DATABASE (role may lack CREATEDB)."""
    import os

    super_url = os.environ.get("SUPERUSER_DATABASE_URL", "").strip()
    if super_url:
        return admin_dsn(super_url) if parse_db_name(super_url) != "postgres" else to_dsn(super_url)
    # Local default used by CPH.1 restore verify (never printed)
    return "postgresql://postgres:botfazer@localhost:5432/postgres"


async def recreate_db_clean(target: str) -> float:
    import asyncpg
    from app.core.config import get_settings

    assert_restore_target(target, allow_recreate=True)
    require_owner_approval()
    t0 = time.perf_counter()
    settings = get_settings()
    source = parse_db_name(settings.database_url)
    if target == source or target in PROTECTED_SOURCE_DBS:
        raise Cph4Error("restore_target_unsafe", f"refused={target}")

    conn = await asyncpg.connect(_superuser_admin_dsn(settings.database_url))
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
    return round(time.perf_counter() - t0, 3)


def restore_dump(*, dump_path: Path, target: str, url_template: str) -> float:
    assert_restore_target(target)
    pg_restore = find_pg_bin("pg_restore")
    u = urlparse(to_dsn(url_template))
    target_url = replace_db(url_template, target)
    t0 = time.perf_counter()
    proc = run_pg(
        [
            str(pg_restore),
            "-h",
            u.hostname or "localhost",
            "-p",
            str(u.port or 5432),
            "-U",
            u.username or "botfazer",
            "-d",
            target,
            "--no-owner",
            "--no-acl",
            "--exit-on-error",
            str(dump_path),
        ],
        url=target_url,
        timeout=900,
    )
    if proc.returncode != 0:
        err = (proc.stderr or "") + (proc.stdout or "")
        raise Cph4Error("restore_failed", err[:600])
    return round(time.perf_counter() - t0, 3)


async def verify_restored_revision(target: str) -> str:
    import asyncpg
    from app.core.config import get_settings

    url = replace_db(get_settings().database_url, target)
    conn = await asyncpg.connect(to_dsn(url))
    try:
        has = await conn.fetchval(
            "select exists(select 1 from information_schema.tables "
            "where table_schema='public' and table_name='alembic_version')"
        )
        if not has:
            raise Cph4Error("restored_revision_unknown", "alembic_version_missing")
        rows = await conn.fetch("select version_num from alembic_version")
        revs = [r["version_num"] for r in rows]
        if len(revs) != 1:
            raise Cph4Error("restored_revision_unknown", f"revs={revs}")
        if revs[0] != EXPECTED_REVISION:
            raise Cph4Error(
                "backup_revision_mismatch",
                f"restored={revs[0]} expected={EXPECTED_REVISION}",
            )
        return revs[0]
    finally:
        await conn.close()


async def drop_restore_db(target: str) -> None:
    import asyncpg

    assert_restore_target(target)
    conn = await asyncpg.connect(_superuser_admin_dsn(""))
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=$1 AND pid <> pg_backend_pid()",
            target,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{target}"')
        print("dropped=", target)
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="CPH.4 restore to disposable DB")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--target", required=True, help="botfazer_cph4_restore_<run_id>")
    args = parser.parse_args()
    try:
        assert_restore_target(args.target)
        verified = verify_backup(Path(args.manifest))
        dump = Path(verified["path"])
        from app.core.config import get_settings

        settings = get_settings()
        print("restore_target=", args.target)
        print("backup_id=", verified["backup_id"])
        print("database_url_template_safe=", safe_url(settings.database_url))

        create_secs = asyncio.run(recreate_db_clean(args.target))
        restore_secs = restore_dump(
            dump_path=dump, target=args.target, url_template=settings.database_url
        )
        rev = asyncio.run(verify_restored_revision(args.target))

        result = {
            "ok": True,
            "restore_database": args.target,
            "restored_revision": rev,
            "restored_at": now_iso(),
            "timings_seconds": {
                "create_database": create_secs,
                "restore": restore_secs,
            },
            "backup_id": verified["backup_id"],
            "sha256": verified["sha256"],
        }
        print(json.dumps(result, indent=2))
        return 0
    except Cph4Error as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
