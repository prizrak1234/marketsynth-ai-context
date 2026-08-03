"""Redis connectivity tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_redis_connection(fake_redis: object) -> None:
    from app.core import redis as redis_module

    await redis_module.init_redis()
    assert await redis_module.check_redis_connection() is True
