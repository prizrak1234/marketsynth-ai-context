"""CPH.1 — compare local PG tables against commercial MVP expectations."""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from scripts.cph1_inventory_postgresql import COMMERCIAL, _to_dsn


async def main() -> None:
    import asyncpg

    conn = await asyncpg.connect(_to_dsn(get_settings().database_url))
    ai60x = [
        "campaign_learnings",
        "project_insights",
        "project_goals",
        "project_decisions",
        "decision_outcome_evidence",
    ]
    for t in ai60x + COMMERCIAL:
        exists = await conn.fetchval(
            "select exists("
            "select 1 from information_schema.tables "
            "where table_schema='public' and table_name=$1)",
            t,
        )
        print(f"{t}.exists={exists}")
        if exists:
            cols = await conn.fetch(
                "select column_name from information_schema.columns "
                "where table_schema='public' and table_name=$1 "
                "order by ordinal_position",
                t,
            )
            print(f"{t}.columns=", [c["column_name"] for c in cols])
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
