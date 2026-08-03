"""Transaction boundary helpers for the service layer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transactional(session: AsyncSession) -> AsyncIterator[None]:
    """Commit on success, rollback on any exception."""
    try:
        yield
        await session.commit()
    except Exception:
        await session.rollback()
        raise
