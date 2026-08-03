"""KG.2 — Knowledge Governance lifecycle transitions (immutable versions)."""

from __future__ import annotations

from app.schemas.contracts import KnowledgeGovernanceStatus

# Allowed transitions (from → frozenset[to])
ALLOWED_TRANSITIONS: dict[KnowledgeGovernanceStatus, frozenset[KnowledgeGovernanceStatus]] = {
    KnowledgeGovernanceStatus.DRAFT: frozenset(
        {KnowledgeGovernanceStatus.VALIDATED, KnowledgeGovernanceStatus.ARCHIVED}
    ),
    KnowledgeGovernanceStatus.VALIDATED: frozenset(
        {
            KnowledgeGovernanceStatus.PUBLISHED,
            KnowledgeGovernanceStatus.DRAFT,  # reject back
            KnowledgeGovernanceStatus.ARCHIVED,
        }
    ),
    KnowledgeGovernanceStatus.PUBLISHED: frozenset(
        {
            KnowledgeGovernanceStatus.DEPRECATED,
            KnowledgeGovernanceStatus.SUPERSEDED,
            KnowledgeGovernanceStatus.ARCHIVED,
        }
    ),
    KnowledgeGovernanceStatus.DEPRECATED: frozenset(
        {KnowledgeGovernanceStatus.ARCHIVED}
    ),
    KnowledgeGovernanceStatus.SUPERSEDED: frozenset(
        {KnowledgeGovernanceStatus.ARCHIVED}
    ),
    KnowledgeGovernanceStatus.ARCHIVED: frozenset(),
}

FORBIDDEN_REASONS = {
    ("draft", "published"): "draft_to_published_forbidden",
    ("archived", "published"): "archived_to_published_forbidden",
}


class LifecycleError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def can_transition(
    current: KnowledgeGovernanceStatus | str,
    target: KnowledgeGovernanceStatus | str,
) -> bool:
    cur = (
        current
        if isinstance(current, KnowledgeGovernanceStatus)
        else KnowledgeGovernanceStatus(str(current))
    )
    tgt = (
        target
        if isinstance(target, KnowledgeGovernanceStatus)
        else KnowledgeGovernanceStatus(str(target))
    )
    return tgt in ALLOWED_TRANSITIONS.get(cur, frozenset())


def assert_transition(
    current: KnowledgeGovernanceStatus | str,
    target: KnowledgeGovernanceStatus | str,
) -> None:
    cur_s = current.value if hasattr(current, "value") else str(current)
    tgt_s = target.value if hasattr(target, "value") else str(target)
    key = (cur_s, tgt_s)
    if key in FORBIDDEN_REASONS:
        raise LifecycleError(FORBIDDEN_REASONS[key], f"Transition {cur_s}→{tgt_s} forbidden")
    if not can_transition(current, target):
        raise LifecycleError(
            "invalid_lifecycle_transition",
            f"Transition {cur_s}→{tgt_s} is not allowed",
        )


def assert_publish_requirements(
    *,
    owner_user_id,
    reviewer_user_id,
    review_date,
    next_review_at,
    source_uri: str,
    content: str,
) -> None:
    if owner_user_id is None:
        raise LifecycleError("owner_required", "Published knowledge requires owner")
    if reviewer_user_id is None:
        raise LifecycleError("reviewer_required", "Published knowledge requires reviewer")
    if review_date is None:
        raise LifecycleError("review_date_required", "Published knowledge requires review_date")
    if next_review_at is None:
        raise LifecycleError(
            "next_review_required", "Published knowledge requires next_review_at"
        )
    if not (source_uri or "").strip():
        raise LifecycleError("source_required", "Published knowledge requires source_uri")
    if not (content or "").strip():
        raise LifecycleError("content_required", "Published knowledge requires content")
