"""MarketingStrategy domain rules (Commercial MVP P0.6).

MarketingStrategy ≠ MarketingPlan.
Eligible only from approved GO / CONDITIONAL_GO BusinessVerdict.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.exceptions import InvalidStateError
from app.db.models.business_verdict import BusinessVerdictTable
from app.schemas.contracts import (
    BusinessVerdictLifecycleStatus,
    MarketingStrategyReadinessStatus,
    StrategyChannelStatus,
    StrategyPositioning,
    StrategyPriceMode,
    StrategyVerdictConditionLink,
    VerdictKind,
)

_BANNED_POSITIONING = (
    r"\binnovative solution\b",
    r"\bunique ecosystem\b",
    r"\bbest service\b",
    r"\brevolutionary platform\b",
    r"\bинновационн\w*\b",
    r"\bуникальн\w+\s+экосистем",
    r"\bлучший сервис\b",
    r"\bреволюционн\w*\b",
)


def assert_verdict_allows_strategy(verdict: BusinessVerdictTable) -> None:
    status = BusinessVerdictLifecycleStatus(verdict.lifecycle_status)
    if status != BusinessVerdictLifecycleStatus.APPROVED:
        raise InvalidStateError("verdict_not_approved")
    vtype = VerdictKind(verdict.verdict_type)
    if vtype not in (VerdictKind.GO, VerdictKind.CONDITIONAL_GO):
        raise InvalidStateError("verdict_type_not_eligible")


def copy_verdict_conditions(
    conditions_raw: list[Any],
) -> list[StrategyVerdictConditionLink]:
    out: list[StrategyVerdictConditionLink] = []
    for c in conditions_raw or []:
        data = c if isinstance(c, dict) else (
            c.model_dump() if hasattr(c, "model_dump") else dict(c)
        )
        cid = str(data.get("id") or "")
        if not cid:
            continue
        status = str(data.get("status") or "open")
        blocking = status in ("open", "in_progress", "failed")
        out.append(
            StrategyVerdictConditionLink(
                verdict_condition_id=cid,
                current_status_snapshot=status,
                strategy_response="Preserve Verdict condition authority; validate only",
                validation_action=str(data.get("required_action") or "")[:2000] or None,
                impact_on_strategy="Blocks planning readiness until Verdict updates status",
                blocking_effect=blocking,
            )
        )
    return out


def validate_positioning(positioning: StrategyPositioning) -> None:
    blob = " ".join(
        [
            positioning.primary_differentiation,
            positioning.key_message,
            positioning.category,
            positioning.proof or "",
        ]
    ).lower()
    for pat in _BANNED_POSITIONING:
        if re.search(pat, blob, flags=re.IGNORECASE):
            raise InvalidStateError("verdict_type_not_eligible")
    if len(positioning.primary_differentiation.strip()) < 12:
        raise InvalidStateError("verdict_type_not_eligible")


def validate_offers_prices(offers: list[Any]) -> None:
    for offer in offers:
        mode = offer.price_model if hasattr(offer, "price_model") else offer.get("price_model")
        value = (
            offer.price_value_or_range
            if hasattr(offer, "price_value_or_range")
            else offer.get("price_value_or_range")
        )
        if mode == StrategyPriceMode.EXACT and not (value or "").strip():
            raise InvalidStateError("verdict_type_not_eligible")


def validate_channel_mix(channels: list[Any]) -> None:
    if not channels:
        raise InvalidStateError("verdict_type_not_eligible")
    recommended = 0
    for ch in channels:
        status = ch.status if hasattr(ch, "status") else ch.get("status")
        if status == StrategyChannelStatus.RECOMMENDED or status == "recommended":
            recommended += 1
    # Never recommend "all" — cap implied by requiring not every channel recommended without exclusions
    if recommended > 6:
        raise InvalidStateError("verdict_type_not_eligible")


def compute_strategy_readiness(
    *,
    verdict_type: VerdictKind,
    objectives: list[Any],
    segments: list[Any],
    positioning: StrategyPositioning | dict[str, Any],
    offers: list[Any],
    channels: list[Any],
    metrics: list[Any],
    verdict_conditions: list[StrategyVerdictConditionLink] | list[dict[str, Any]],
    assumptions: list[Any],
) -> MarketingStrategyReadinessStatus:
    blocking = False
    for c in verdict_conditions:
        effect = c.blocking_effect if hasattr(c, "blocking_effect") else c.get("blocking_effect")
        status = (
            c.current_status_snapshot
            if hasattr(c, "current_status_snapshot")
            else c.get("current_status_snapshot")
        )
        if effect and status in ("open", "in_progress", "failed"):
            blocking = True
    for a in assumptions:
        st = a.status if hasattr(a, "status") else a.get("status")
        if st == "invalidated":
            return MarketingStrategyReadinessStatus.BLOCKED

    has_obj = len(objectives) > 0
    has_seg = len(segments) > 0
    pos = positioning if isinstance(positioning, dict) else positioning.model_dump()
    has_pos = bool(pos.get("primary_differentiation") and pos.get("key_message"))
    has_offer = len(offers) > 0
    has_ch = len(channels) > 0
    has_met = len(metrics) > 0

    if not (has_obj and has_seg and has_pos and has_offer and has_ch and has_met):
        return MarketingStrategyReadinessStatus.NOT_READY
    if blocking or verdict_type == VerdictKind.CONDITIONAL_GO:
        return MarketingStrategyReadinessStatus.CONDITIONALLY_READY
    return MarketingStrategyReadinessStatus.READY_FOR_PLANNING
