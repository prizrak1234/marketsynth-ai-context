"""CPH.1 — safe PostgreSQL inventory (no secrets, no row dumps)."""

from __future__ import annotations

import asyncio
import re
import sys


COMMERCIAL = [
    "projects",
    "project_briefs",
    "investigations",
    "sources",
    "investigation_source_links",
    "investigation_evidence",
    "evidence_source_links",
    "business_verdicts",
    "business_verdict_evidence_snapshots",
    "business_verdict_evidence_links",
    "marketing_strategies",
    "implementation_plans",
    "implementation_marketing_plan_handoffs",
    "marketing_plans",
    "users",
]


def _safe_url(url: str) -> str:
    return re.sub(r"://([^:/]+):([^@]+)@", r"://\1:***@", url)


def _to_dsn(url: str) -> str:
    for p in (
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
        "postgresql+psycopg2://",
    ):
        if url.startswith(p):
            return "postgresql://" + url[len(p) :]
    return url


async def main() -> int:
    from app.core.config import get_settings

    settings = get_settings()
    url = settings.database_url
    print("database_url_safe=", _safe_url(url))
    dsn = _to_dsn(url)
    try:
        import asyncpg
    except ImportError:
        print("error=asyncpg_missing")
        return 2

    try:
        conn = await asyncpg.connect(dsn)
    except Exception as exc:  # noqa: BLE001
        print("connect_error=", type(exc).__name__, str(exc)[:240])
        return 1

    ver = await conn.fetchval("select version()")
    print("pg_version=", str(ver).split(",")[0][:100])
    print("database=", await conn.fetchval("select current_database()"))
    schemas = await conn.fetch(
        "select schema_name from information_schema.schemata "
        "where schema_name not in ('pg_catalog','information_schema') order by 1"
    )
    print("schemas=", [r["schema_name"] for r in schemas])

    has_alembic = await conn.fetchval(
        "select exists(select 1 from information_schema.tables "
        "where table_schema='public' and table_name='alembic_version')"
    )
    if has_alembic:
        rows = await conn.fetch("select version_num from alembic_version")
        print("alembic_version=", [r["version_num"] for r in rows])
    else:
        print("alembic_version=", None)

    tables = await conn.fetch(
        "select table_name from information_schema.tables "
        "where table_schema='public' and table_type='BASE TABLE' "
        "order by table_name"
    )
    names = [r["table_name"] for r in tables]
    print("table_count=", len(names))
    print("tables=", ",".join(names))

    for t in COMMERCIAL:
        if t in names:
            n = await conn.fetchval(f'select count(*) from "{t}"')
            print(f"count.{t}=", n)
        else:
            print(f"missing.{t}=", True)

    size = await conn.fetchval("select pg_size_pretty(pg_database_size(current_database()))")
    print("db_size=", size)
    await conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
