"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session as _get_session_from_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session; closed after the request."""
    async for session in _get_session_from_factory():
        yield session
