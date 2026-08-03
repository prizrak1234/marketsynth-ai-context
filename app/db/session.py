"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    cfg = settings or get_settings()
    return create_async_engine(
        cfg.database_url,
        echo=cfg.database_echo,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db(settings: Settings | None = None) -> None:
    """Create engine and session factory (called on app startup)."""
    global _engine, _session_factory
    cfg = settings or get_settings()
    _engine = create_engine(cfg)
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    import app.db.models  # noqa: F401 — register mappers before enum alignment

    from app.db.base import align_postgres_enum_columns

    align_postgres_enum_columns()


async def close_db() -> None:
    """Dispose engine on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def check_database_connection() -> bool:
    """Return True if database accepts a simple query."""
    from sqlalchemy import text

    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def reset_db_state() -> None:
    """Reset globals — for tests only."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
