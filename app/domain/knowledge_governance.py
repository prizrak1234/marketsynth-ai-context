"""Knowledge Governance — pure policy helpers (no retrieval / VectorDB / LLM)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.contracts import (
    KnowledgeFreshnessCheck,
    KnowledgeFreshnessState,
    KnowledgeGovernanceStatus,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def evaluate_knowledge_freshness(
    *,
    knowledge_id,
    status: KnowledgeGovernanceStatus | str,
    review_date: datetime | None,
    next_review: datetime | None,
    as_of: datetime | None = None,
) -> KnowledgeFreshnessCheck:
    """Automatic freshness check from ReviewDate / NextReview / status."""
    when = as_of or _now()
    if when.tzinfo is not None:
        when = when.replace(tzinfo=None)
    if review_date is not None and review_date.tzinfo is not None:
        review_date = review_date.replace(tzinfo=None)
    if next_review is not None and next_review.tzinfo is not None:
        next_review = next_review.replace(tzinfo=None)
    status_v = status.value if hasattr(status, "value") else str(status)

    if status_v == KnowledgeGovernanceStatus.DEPRECATED.value:
        return KnowledgeFreshnessCheck(
            knowledge_id=knowledge_id,
            review_date=review_date,
            next_review=next_review,
            freshness=KnowledgeFreshnessState.DEPRECATED,
            expired=False,
            deprecated=True,
            safe_message="Знание помечено как deprecated и не должно использоваться как операционная истина.",
        )

    if status_v in {
        KnowledgeGovernanceStatus.ARCHIVED.value,
        KnowledgeGovernanceStatus.SUPERSEDED.value,
    }:
        return KnowledgeFreshnessCheck(
            knowledge_id=knowledge_id,
            review_date=review_date,
            next_review=next_review,
            freshness=KnowledgeFreshnessState.DEPRECATED
            if status_v == KnowledgeGovernanceStatus.SUPERSEDED.value
            else KnowledgeFreshnessState.UNKNOWN,
            expired=False,
            deprecated=status_v == KnowledgeGovernanceStatus.SUPERSEDED.value,
            safe_message="Знание не в статусе published.",
        )

    if next_review is not None and when > next_review:
        return KnowledgeFreshnessCheck(
            knowledge_id=knowledge_id,
            review_date=review_date,
            next_review=next_review,
            freshness=KnowledgeFreshnessState.EXPIRED,
            expired=True,
            deprecated=False,
            safe_message="Срок NextReview истёк — требуется повторный review перед использованием.",
        )

    if next_review is not None:
        days_left = (next_review - when).days
        # 7–14 day owner review window before expiry
        if 0 <= days_left <= 14:
            return KnowledgeFreshnessCheck(
                knowledge_id=knowledge_id,
                review_date=review_date,
                next_review=next_review,
                freshness=KnowledgeFreshnessState.DUE_FOR_REVIEW,
                expired=False,
                deprecated=False,
                safe_message=(
                    f"До NextReview осталось {days_left} дн. — владельцу нужна задача на review."
                ),
            )
        return KnowledgeFreshnessCheck(
            knowledge_id=knowledge_id,
            review_date=review_date,
            next_review=next_review,
            freshness=KnowledgeFreshnessState.FRESH,
            expired=False,
            deprecated=False,
            safe_message="Знание в пределах окна NextReview.",
        )

    if review_date is None and next_review is None:
        return KnowledgeFreshnessCheck(
            knowledge_id=knowledge_id,
            review_date=None,
            next_review=None,
            freshness=KnowledgeFreshnessState.UNKNOWN,
            expired=False,
            deprecated=False,
            safe_message="ReviewDate / NextReview не заданы.",
        )

    return KnowledgeFreshnessCheck(
        knowledge_id=knowledge_id,
        review_date=review_date,
        next_review=next_review,
        freshness=KnowledgeFreshnessState.DUE_FOR_REVIEW,
        expired=False,
        deprecated=False,
        safe_message="Требуется назначить NextReview.",
    )


def citation_contract_is_complete(citation: dict | object) -> bool:
    """Invariant: Answer + Evidence + Source + Confidence must be present."""
    if hasattr(citation, "model_dump"):
        data = citation.model_dump()
    elif isinstance(citation, dict):
        data = citation
    else:
        return False
    answer = str(data.get("answer") or "").strip()
    source = str(data.get("source") or "").strip()
    confidence = data.get("confidence")
    evidence = data.get("evidence")
    if not answer or not source or confidence is None:
        return False
    if not isinstance(evidence, list):
        return False
    return True
