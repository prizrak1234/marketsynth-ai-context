"""Read-only Redis depth probes for handoff queues (Phase 3.11)."""

from __future__ import annotations

from uuid import UUID

from app.core.redis import get_redis
from app.core.security import sanitize_text
from app.queues.handoff_child_queue import HANDOFF_OWNERS_SET_KEY, handoff_queue_key
from app.queues.handoff_dead_letter_queue import HANDOFF_DLQ_OWNERS_SET_KEY, handoff_dlq_key


async def get_owner_queue_depth(owner_id: UUID) -> int:
    redis = get_redis()
    return int(await redis.llen(handoff_queue_key(owner_id)))


async def get_dlq_depth(owner_id: UUID) -> int:
    redis = get_redis()
    return int(await redis.llen(handoff_dlq_key(owner_id)))


async def get_known_queue_owners() -> list[UUID]:
    redis = get_redis()
    members = await redis.smembers(HANDOFF_OWNERS_SET_KEY)
    return [UUID(str(member)) for member in sorted(members)]


async def get_known_dlq_owners() -> list[UUID]:
    redis = get_redis()
    members = await redis.smembers(HANDOFF_DLQ_OWNERS_SET_KEY)
    return [UUID(str(member)) for member in sorted(members)]


async def count_known_queue_owners() -> int:
    owners = await get_known_queue_owners()
    dlq_owners = await get_known_dlq_owners()
    return len(set(owners) | set(dlq_owners))


def _safe_redis_error(exc: Exception) -> str:
    cleaned = sanitize_text(str(exc) or "redis_unavailable")
    return cleaned[:200] if len(cleaned) > 200 else cleaned


async def get_owner_redis_metrics(owner_id: UUID) -> dict[str, object]:
    """Return queue depths; never raises — sets available=false on failure."""
    try:
        return {
            "available": True,
            "queue_depth": await get_owner_queue_depth(owner_id),
            "dlq_depth": await get_dlq_depth(owner_id),
            "error": None,
        }
    except Exception as exc:
        return {
            "available": False,
            "queue_depth": 0,
            "dlq_depth": 0,
            "error": _safe_redis_error(exc),
        }
