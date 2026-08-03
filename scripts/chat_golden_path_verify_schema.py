#!/usr/bin/env python3
"""Verify chat golden path DB schema on botfazer_cph1."""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory, init_db, reset_db_state

COLUMNS = (
    "client_message_id",
    "idempotency_key",
    "conversation_id",
    "sequence_number",
    "assistant_run_id",
    "routing_decision_id",
    "chat_route",
)


async def main() -> None:
    reset_db_state()
    await init_db(get_settings())
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'user_requests'
                  AND column_name = ANY(:cols)
                ORDER BY column_name
                """
            ),
            {"cols": list(COLUMNS)},
        )
        found = [row[0] for row in result.fetchall()]
        print("columns_found:", found)
        missing = sorted(set(COLUMNS) - set(found))
        if missing:
            raise SystemExit(f"missing_columns={missing}")

        idx = await session.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'user_requests'
                  AND (
                    indexname LIKE '%client_message%'
                    OR indexname LIKE '%idempotency%'
                  )
                ORDER BY indexname
                """
            ),
        )
        indexes = [row[0] for row in idx.fetchall()]
        print("indexes_found:", indexes)
        if len(indexes) < 2:
            raise SystemExit(f"expected_at_least_2_indexes got={indexes}")
    print("schema_ok")


if __name__ == "__main__":
    asyncio.run(main())
