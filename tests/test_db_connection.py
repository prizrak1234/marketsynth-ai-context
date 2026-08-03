"""Database connectivity tests."""

from __future__ import annotations

import pytest
from app.db.session import check_database_connection, get_engine, init_db, reset_db_state
from sqlmodel import SQLModel


@pytest.mark.asyncio
async def test_database_connection(database_url: str) -> None:
    reset_db_state()
    await init_db()
    async with get_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    assert await check_database_connection() is True
