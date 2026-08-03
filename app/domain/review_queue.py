"""Human review queue predicates (Phase 14.0)."""

from __future__ import annotations

from app.marketing.contracts import ContentAssetStatus


def asset_requires_human_review(
    *,
    status: ContentAssetStatus,
    current_version_number: int,
    approved_version_number: int | None,
) -> bool:
    """True when asset is in review awaiting human approval (Phase AI.42)."""
    _ = (current_version_number, approved_version_number)
    return status == ContentAssetStatus.REVIEW
