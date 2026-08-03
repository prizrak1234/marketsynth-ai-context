"""Internal Offer Builder runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

SKILL_ID = "ms.skill.offer_builder"
SKILL_VERSION = "0.1.0"
PACKAGE_HASH = "b637c3920066953f3080c8dc3e7c58bc08dc95138a85c545cac04d80a04d02f4"

MARKET_VALIDATION_SKILL = "ms.skill.market_validation"
MARKET_VALIDATION_VERSION = "0.2.0"
POSITIONING_SKILL = "ms.skill.positioning"
POSITIONING_VERSION = "0.1.0"
CLAIMS_SKILL = "ms.skill.claim_substantiation"
CLAIMS_VERSION = "0.1.0"
CIM_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    allowed: bool
    blocker_code: str | None = None
    mv_verdict: str = "proceed"


@dataclass(frozen=True, slots=True)
class UpstreamBundle:
    market_validation: dict[str, Any]
    positioning: dict[str, Any]
    claim_substantiation: dict[str, Any]
    cim: dict[str, Any]
    mv_verdict: str
    positioning_hypothesis_id: str
    substantiated_claim_ids: tuple[str, ...]
    inherited_conditions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    inherited_blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class OfferGenerationContext:
    owner_id: UUID
    project_id: UUID
    launch_pack_request_id: UUID
    business_verdict_id: UUID
    user_request_id: UUID
    upstream: UpstreamBundle
    launch_objective: str = ""
