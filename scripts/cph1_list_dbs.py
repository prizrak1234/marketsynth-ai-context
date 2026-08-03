"""List local botfazer databases and privileges."""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from scripts.cph1_db_tools import admin_dsn


async def main() -> None:
    import asyncpg

    settings = get_settings()
    conn = await asyncpg.connect(admin_dsn(settings.database_url))
    try:
        rows = await conn.fetch(
            "select datname from pg_database where datname like 'botfazer%' order by 1"
        )
        print("dbs=", [r["datname"] for r in rows])
        print("current_user=", await conn.fetchval("select current_user"))
        print(
            "rolcreatedb=",
            await conn.fetchval(
                "select rolcreatedb from pg_roles where rolname=current_user"
            ),
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
