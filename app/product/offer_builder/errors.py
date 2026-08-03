"""Offer Builder domain errors — mapped to InvalidStateError codes."""

from __future__ import annotations

OFFER_BLOCKER_CODES = frozenset(
    {
        "blocked_by_verdict",
        "blocked_by_missing_positioning",
        "blocked_by_claims",
        "blocked_by_evidence",
        "blocked_by_missing_cim",
        "blocked_by_hash_mismatch",
        "blocked_by_tenant_scope",
        "offer_generation_failed",
        "stale_approval_hash",
        "invalid_state_transition",
        "offer_not_found",
        "launch_pack_not_found",
        "launch_pack_not_eligible",
    }
)
