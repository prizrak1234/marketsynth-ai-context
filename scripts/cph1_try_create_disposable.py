"""Try create disposable DB using optional SUPERUSER_DATABASE_URL (never logged)."""

from __future__ import annotations

import asyncio
import os
import sys

from scripts.cph1_db_tools import (
    SAFE_DISPOSABLE_DBS,
    admin_dsn,
    assert_disposable,
    replace_db,
    safe_url,
    to_dsn,
)


async def main(db_name: str = "botfazer_cph1") -> int:
    import asyncpg
    from app.core.config import get_settings

    assert_disposable(db_name)
    settings = get_settings()
    super_url = os.environ.get("SUPERUSER_DATABASE_URL") or os.environ.get(
        "POSTGRES_SUPERUSER_URL"
    )
    if super_url:
        dsn = to_dsn(super_url)
        # force maintenance DB
        from urllib.parse import urlparse

        u = urlparse(dsn)
        dsn = f"{u.scheme}://{u.netloc}/postgres"
        print("using_superuser_url=", True)
        print("super_url_safe=", safe_url(dsn))
    else:
        dsn = admin_dsn(settings.database_url)
        print("using_app_user_admin=", True)
        print("url_safe=", safe_url(dsn))

    conn = await asyncpg.connect(dsn)
    try:
        me = await conn.fetchval("select current_user")
        createdb = await conn.fetchval(
            "select rolcreatedb from pg_roles where rolname=current_user"
        )
        print("current_user=", me)
        print("rolcreatedb=", createdb)
        if not createdb and me != "postgres":
            print(
                "blocked=insufficient_privilege; "
                "run as PostgreSQL superuser: "
                f'CREATE DATABASE {db_name} OWNER botfazer;'
            )
            print(
                "or set SUPERUSER_DATABASE_URL and re-run: "
                "uv run python scripts/cph1_try_create_disposable.py"
            )
            return 5
        exists = await conn.fetchval(
            "select 1 from pg_database where datname=$1", db_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}" OWNER botfazer')
            print("created=", db_name)
        else:
            print("already_exists=", db_name)
    finally:
        await conn.close()
    print("target=", safe_url(replace_db(settings.database_url, db_name)))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "botfazer_cph1")))
