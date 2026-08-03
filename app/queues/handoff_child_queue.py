"""Per-owner Redis FIFO for queued handoff child agent runs (Phase 3.7)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.config import get_settings
from app.core.redis import get_redis

HANDOFF_OWNERS_SET_KEY = "botfazer:graph:handoff:owners"


def handoff_queue_key(owner_id: UUID) -> str:
    return f"botfazer:graph:handoff:queue:{owner_id}"


@dataclass(frozen=True)
class HandoffChildQueueItem:
    owner_id: UUID
    run_id: UUID


class HandoffChildQueue:
    """Enqueue handoff children for async worker / scheduler drainage."""

    def is_enabled(self) -> bool:
        return get_settings().graph_handoff_queue_enabled

    async def enqueue(self, owner_id: UUID, run_id: UUID) -> bool:
        if not self.is_enabled():
            return False
        redis = get_redis()
        owner_key = str(owner_id)
        await redis.rpush(handoff_queue_key(owner_id), str(run_id))
        await redis.sadd(HANDOFF_OWNERS_SET_KEY, owner_key)
        return True

    async def dequeue_batch(self, owner_id: UUID, *, limit: int) -> list[UUID]:
        if not self.is_enabled():
            return []
        redis = get_redis()
        key = handoff_queue_key(owner_id)
        run_ids: list[UUID] = []
        for _ in range(limit):
            raw = await redis.lpop(key)
            if raw is None:
                break
            run_ids.append(UUID(str(raw)))
        await self._refresh_owner_membership(owner_id)
        return run_ids

    async def _refresh_owner_membership(self, owner_id: UUID) -> None:
        redis = get_redis()
        remaining = await redis.llen(handoff_queue_key(owner_id))
        if remaining == 0:
            await redis.srem(HANDOFF_OWNERS_SET_KEY, str(owner_id))

    async def list_owners_with_pending(self) -> list[UUID]:
        if not self.is_enabled():
            return []
        redis = get_redis()
        members = await redis.smembers(HANDOFF_OWNERS_SET_KEY)
        return [UUID(str(member)) for member in sorted(members)]

    async def pending_count(self, owner_id: UUID) -> int:
        if not self.is_enabled():
            return 0
        redis = get_redis()
        return int(await redis.llen(handoff_queue_key(owner_id)))
