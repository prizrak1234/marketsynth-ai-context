"""Async Redis client — cache, queues, session state (L1)."""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import Settings, get_settings

_redis: Redis | None = None


def create_redis_client(settings: Settings | None = None) -> Redis:
    cfg = settings or get_settings()
    return Redis.from_url(
        cfg.redis_url,
        encoding="utf-8",
        decode_responses=True,
        # Windows Redis 3.x / legacy installs lack RESP3 HELLO.
        protocol=2,
    )


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = create_redis_client()
    return _redis


async def init_redis(settings: Settings | None = None) -> None:
    global _redis
    _redis = create_redis_client(settings)


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
    _redis = None


async def check_redis_connection() -> bool:
    try:
        redis = get_redis()
        pong = await redis.ping()
        return bool(pong)
    except Exception:
        return False


def reset_redis_state() -> None:
    """Reset global client — for tests only."""
    global _redis
    _redis = None
