"""Pytest fixtures — file SQLite + fakeredis for isolation."""

from __future__ import annotations

import asyncio
import os
import random
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("PII_SANITIZER_ENABLED", "true")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _default_content_draft_off(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Keep H2.7 draft execution off unless a test explicitly enables it."""
    monkeypatch.setenv("CONTENT_DRAFT_EXECUTION_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_compiled_agent_graph_cache() -> Generator[None, None, None]:
    from app.graphs.agent_graph import clear_compiled_agent_graph_cache

    clear_compiled_agent_graph_cache()
    yield
    clear_compiled_agent_graph_cache()


@pytest.fixture
def database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    db_file = tmp_path / "test.db"
    url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.core.config import get_settings

    get_settings.cache_clear()
    return url


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> object:
    import fakeredis.aioredis
    from app.core import redis as redis_module

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def _init(_settings: object = None) -> None:
        redis_module._redis = client  # noqa: SLF001

    async def _close() -> None:
        await client.aclose()
        redis_module._redis = None  # noqa: SLF001

    monkeypatch.setattr(redis_module, "init_redis", _init)
    monkeypatch.setattr(redis_module, "close_redis", _close)
    return client


async def _init_database_schema() -> None:
    from app.db.session import get_engine, init_db, reset_db_state

    reset_db_state()
    await init_db()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@pytest.fixture
def app_with_db(database_url: str, fake_redis: object) -> Generator[object, None, None]:
    asyncio.run(_init_database_schema())
    from app.main import app

    yield app
    from app.core.redis import close_redis
    from app.db.session import close_db

    asyncio.run(close_redis())
    asyncio.run(close_db())


@pytest.fixture
def client(app_with_db: object) -> Generator[TestClient, None, None]:
    with TestClient(app_with_db) as test_client:
        yield test_client


@pytest.fixture
def biv_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable BIV async runtime for integration tests."""
    from app.core.config import get_settings

    monkeypatch.setenv("BUSINESS_IDEA_VALIDATION_ENABLED", "true")
    monkeypatch.setenv("MCP_READ_ONLY_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_SOURCE_COLLECTION_MOCK_PROVIDERS", "true")
    monkeypatch.setenv("BIV_RUN_DISPATCHER_ENABLED", "true")
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_session(
    database_url: str,
    fake_redis: object,
) -> AsyncGenerator[AsyncSession, None]:
    from app.core.redis import init_redis

    await _init_database_schema()
    await init_redis()
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        yield session


async def _create_user_with_api_key(
    *,
    telegram_id: int | None = None,
    is_active: bool = True,
) -> tuple[str, object]:
    from app.schemas.crud import UserCreate
    from app.services.auth import AuthService
    from app.services.users_service import UserService

    await _init_database_schema()
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        user_service = UserService(session)
        auth_service = AuthService(session)
        user = await user_service.create(
            UserCreate(
                telegram_id=telegram_id or random.randint(1_000_000, 9_999_999),
                display_name="Test User",
                is_active=is_active,
            ),
        )
        created = await auth_service.create_api_key(user.id, "pytest-key")
        return created.plain_key, user


@pytest.fixture
def auth_headers(database_url: str) -> dict[str, str]:
    plain_key, _user = asyncio.run(_create_user_with_api_key())
    return {"Authorization": f"Bearer {plain_key}"}


@pytest.fixture
def other_auth_headers(database_url: str) -> dict[str, str]:
    plain_key, _user = asyncio.run(_create_user_with_api_key())
    return {"Authorization": f"Bearer {plain_key}"}
