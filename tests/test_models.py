"""SQLModel table mapping tests."""

from __future__ import annotations

import pytest
from app.db.models.user import UserTable
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_user_table_persists(db_session: AsyncSession) -> None:
    user = UserTable(telegram_id=12345, display_name="Test User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.id is not None
    assert user.telegram_id == 12345
    assert user.created_at is not None
