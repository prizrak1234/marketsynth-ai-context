"""Owner/admin review transitions for inventory candidates."""

from __future__ import annotations

from app.knowledge_foundation.admission import transition_on_approve, transition_on_reject
from app.knowledge_foundation.inventory import get_inventory_item
from app.knowledge_foundation.review_store import set_review
from app.schemas.contracts import KnowledgeItem, KnowledgeItemStatus


class KnowledgeReviewError(ValueError):
    pass


def approve_knowledge_item(
    item_id: str,
    *,
    reviewed_by: str,
    note: str | None = None,
) -> KnowledgeItem:
    item = get_inventory_item(item_id)
    if item is None:
        raise KnowledgeReviewError(f"unknown_knowledge_item:{item_id}")
    # Read base status without overlay for transition from seed+overlay.
    next_status = transition_on_approve(item)
    if next_status is None:
        raise KnowledgeReviewError(f"cannot_approve:{item_id}:{item.status.value}")
    set_review(item_id, next_status, reviewed_by=reviewed_by, note=note)
    updated = get_inventory_item(item_id)
    assert updated is not None
    return updated


def reject_knowledge_item(
    item_id: str,
    *,
    reviewed_by: str,
    note: str | None = None,
) -> KnowledgeItem:
    item = get_inventory_item(item_id)
    if item is None:
        raise KnowledgeReviewError(f"unknown_knowledge_item:{item_id}")
    next_status = transition_on_reject(item)
    if next_status is None:
        raise KnowledgeReviewError(f"cannot_reject:{item_id}:{item.status.value}")
    set_review(item_id, KnowledgeItemStatus.REJECTED, reviewed_by=reviewed_by, note=note)
    updated = get_inventory_item(item_id)
    assert updated is not None
    return updated
