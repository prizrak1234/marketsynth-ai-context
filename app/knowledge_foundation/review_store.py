"""In-process review overlay for inventory approve/reject (H2.1 — no PG yet)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas.contracts import KnowledgeItem, KnowledgeItemStatus

_UTC = timezone.utc


@dataclass
class ReviewOverlay:
    status: KnowledgeItemStatus
    reviewed_at: datetime
    reviewed_by: str
    note: str | None = None


_OVERLAY: dict[str, ReviewOverlay] = {}


def get_overlay() -> dict[str, ReviewOverlay]:
    return _OVERLAY


def apply_review_overlay(item: KnowledgeItem) -> KnowledgeItem:
    overlay = _OVERLAY.get(item.id)
    if overlay is None:
        return item
    updated = item.model_copy(deep=True)
    updated.status = overlay.status
    updated.reviewed_at = overlay.reviewed_at
    updated.reviewed_by = overlay.reviewed_by
    if overlay.note:
        updated.notes = overlay.note
    return updated


def set_review(
    item_id: str,
    status: KnowledgeItemStatus,
    *,
    reviewed_by: str,
    note: str | None = None,
) -> None:
    _OVERLAY[item_id] = ReviewOverlay(
        status=status,
        reviewed_at=datetime.now(tz=_UTC),
        reviewed_by=reviewed_by,
        note=note,
    )
