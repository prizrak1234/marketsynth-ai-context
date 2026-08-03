"""Review queue read-only agent tool definitions (Phase 14.1)."""

from __future__ import annotations

from typing import Any

from app.schemas.review_queue import ReviewQueueItem

REVIEW_QUEUE_LIST_TOOL_NAME = "review_queue.list"

REVIEW_QUEUE_LIST_DEFAULT_LIMIT = 50
REVIEW_QUEUE_LIST_MAX_LIMIT = 200

REVIEW_QUEUE_LIST_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": REVIEW_QUEUE_LIST_MAX_LIMIT,
            "default": REVIEW_QUEUE_LIST_DEFAULT_LIMIT,
        },
    },
    "additionalProperties": False,
}


def format_review_queue_list_compact(
    items: list[ReviewQueueItem],
    *,
    count: int,
) -> dict[str, Any]:
    """Compact queue payload for agents — no bodies, versions, or secrets."""
    return {
        "items": [
            {
                "type": item.type.value,
                "id": str(item.id),
                "campaign_id": str(item.campaign_id) if item.campaign_id is not None else None,
                "campaign_title": item.campaign_title,
                "title": item.title,
                "status": item.status.value,
                "current_version_number": item.current_version_number,
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        "count": count,
    }
