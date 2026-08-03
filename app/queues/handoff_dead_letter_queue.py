"""Dead-letter queue for handoff child runs that exceeded max worker attempts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import sanitize_text

HANDOFF_DLQ_OWNERS_SET_KEY = "botfazer:graph:handoff:dlq:owners"


def handoff_dlq_key(owner_id: UUID) -> str:
    return f"botfazer:graph:handoff:dlq:{owner_id}"


@dataclass(frozen=True)
class HandoffDeadLetterEntry:
    owner_id: UUID
    child_run_id: UUID
    parent_run_id: UUID | None
    reason: str
    attempts: int
    failed_at: str
    last_error: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_id": str(self.owner_id),
            "child_run_id": str(self.child_run_id),
            "parent_run_id": str(self.parent_run_id) if self.parent_run_id else "",
            "reason": self.reason,
            "attempts": self.attempts,
            "failed_at": self.failed_at,
            "last_error": self.last_error,
        }


class HandoffDeadLetterQueue:
    def is_enabled(self) -> bool:
        return get_settings().graph_handoff_dlq_enabled

    async def push(self, entry: HandoffDeadLetterEntry) -> bool:
        if not self.is_enabled():
            return False
        redis = get_redis()
        payload = json.dumps(entry.to_dict(), separators=(",", ":"))
        await redis.rpush(handoff_dlq_key(entry.owner_id), payload)
        await redis.sadd(HANDOFF_DLQ_OWNERS_SET_KEY, str(entry.owner_id))
        return True

    async def list_entries(self, owner_id: UUID, *, limit: int = 100) -> list[dict[str, Any]]:
        if not self.is_enabled():
            return []
        redis = get_redis()
        raw_items = await redis.lrange(handoff_dlq_key(owner_id), 0, max(0, limit - 1))
        entries: list[dict[str, Any]] = []
        for raw in raw_items:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                entries.append(parsed)
        return entries


def sanitize_handoff_worker_error(message: str, *, max_length: int = 500) -> str:
    cleaned = sanitize_text(message or "handoff_worker_error")
    if len(cleaned) > max_length:
        return cleaned[:max_length]
    return cleaned
