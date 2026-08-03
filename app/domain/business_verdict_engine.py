"""BusinessVerdict domain rules (Commercial MVP P0.5).

Readiness ≠ verdict type.
Verdict approval ≠ execution / publication / Strategy creation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from app.core.exceptions import InvalidStateError
from app.db.models.evidence import InvestigationEvidenceTable
from app.schemas.contracts import (
    BusinessVerdictConfidenceLevel,
    BusinessVerdictEvidenceRole,
    BusinessVerdictLifecycleStatus,
    EvidenceAssessmentState,
    EvidenceLifecycleStatus,
    EvidenceMateriality,
    InvestigationStatus,
    VerdictCondition,
    VerdictConditionStatus,
    VerdictCriticalRisk,
    VerdictKind,
    VerdictReadinessStatus,
    VerdictSensitivity,
    BusinessVerdictStrategyEligibility,
)


def map_readiness_from_contribution(contribution: str) -> VerdictReadinessStatus:
    if contribution == "sufficient":
        return VerdictReadinessStatus.READY_FOR_REVIEW
    if contribution == "blocked":
        return VerdictReadinessStatus.NOT_READY
    return VerdictReadinessStatus.CONDITIONALLY_READY


def compute_snapshot_hash(
    *,
    project_id: UUID,
    investigation_id: UUID,
    evidence_versions: dict[str, int],
) -> str:
    payload = {
        "project_id": str(project_id),
        "investigation_id": str(investigation_id),
        "evidence_versions": dict(sorted(evidence_versions.items())),
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def snapshot_stats(
    rows: list[InvestigationEvidenceTable],
) -> dict[str, Any]:
    evidence_ids: list[str] = []
    evidence_versions: dict[str, int] = {}
    area_coverage: dict[str, int] = {}
    accepted = 0
    missing_critical = 0
    conflicting_critical = 0
    outdated_critical = 0
    for row in rows:
        eid = str(row.id)
        evidence_ids.append(eid)
        evidence_versions[eid] = int(row.version)
        area = str(row.investigation_area)
        area_coverage[area] = area_coverage.get(area, 0) + 1
        if row.lifecycle_status == EvidenceLifecycleStatus.ACCEPTED:
            accepted += 1
        critical = row.materiality == EvidenceMateriality.CRITICAL
        if critical and row.assessment_state == EvidenceAssessmentState.MISSING:
            missing_critical += 1
        if critical and row.assessment_state == EvidenceAssessmentState.CONFLICTING:
            conflicting_critical += 1
        if critical and row.assessment_state == EvidenceAssessmentState.OUTDATED:
            outdated_critical += 1
    return {
        "evidence_ids": evidence_ids,
        "evidence_versions": evidence_versions,
        "accepted_evidence_count": accepted,
        "missing_critical_count": missing_critical,
        "conflicting_critical_count": conflicting_critical,
        "outdated_critical_count": outdated_critical,
        "area_coverage": area_coverage,
    }


def has_area_coverage(area_coverage: dict[str, int], *areas: str) -> bool:
    return all(area_coverage.get(a, 0) > 0 for a in areas)


def compute_strategy_eligibility(
    *,
    verdict_type: VerdictKind,
    lifecycle_status: BusinessVerdictLifecycleStatus,
    conditions: list[VerdictCondition] | list[dict[str, Any]],
) -> BusinessVerdictStrategyEligibility:
    base = BusinessVerdictStrategyEligibility(
        creates_strategy=False,
        creates_execution_approval=False,
        creates_publication_approval=False,
        creates_agent_run=False,
    )
    if lifecycle_status != BusinessVerdictLifecycleStatus.APPROVED:
        return base.model_copy(
            update={
                "strategy_eligible": False,
                "strategy_blocked_reason": f"verdict_not_approved:{lifecycle_status.value}",
            }
        )

    open_conditions = False
    for c in conditions:
        status = c.status if hasattr(c, "status") else c.get("status")
        if status in (VerdictConditionStatus.OPEN, VerdictConditionStatus.IN_PROGRESS, "open", "in_progress"):
            open_conditions = True
            break

    if verdict_type == VerdictKind.GO:
        return base.model_copy(update={"strategy_eligible": True, "open_conditions_mandatory": False})
    if verdict_type == VerdictKind.CONDITIONAL_GO:
        return base.model_copy(
            update={
                "strategy_eligible": True,
                "open_conditions_mandatory": open_conditions,
            }
        )
    if verdict_type == VerdictKind.NO_GO:
        return base.model_copy(
            update={
                "strategy_eligible": False,
                "strategy_blocked_reason": "approved_no_go",
                "pivot_route_allowed": True,
            }
        )
    return base.model_copy(
        update={
            "strategy_eligible": False,
            "strategy_blocked_reason": "approved_insufficient_data",
            "return_to_investigation": True,
        }
    )


def validate_verdict_type_against_readiness(
    verdict_type: VerdictKind,
    readiness: VerdictReadinessStatus,
) -> None:
    """Readiness constrains allowed draft types — never selects the type."""

    if readiness == VerdictReadinessStatus.NOT_READY and verdict_type != VerdictKind.INSUFFICIENT_DATA:
        raise InvalidStateError("verdict_type_not_allowed")
    if readiness == VerdictReadinessStatus.CONDITIONALLY_READY and verdict_type not in (
        VerdictKind.CONDITIONAL_GO,
        VerdictKind.INSUFFICIENT_DATA,
        VerdictKind.NO_GO,
    ):
        # CONDITIONAL_GO or INSUFFICIENT_DATA preferred; NO_GO allowed if risks clear
        if verdict_type == VerdictKind.GO:
            raise InvalidStateError("verdict_type_not_allowed")


def validate_evidence_roles_for_type(
    *,
    verdict_type: VerdictKind,
    roles: list[BusinessVerdictEvidenceRole],
    missing_critical: int,
    conflicting_critical: int,
    outdated_critical: int,
    conditions: list[VerdictCondition],
    critical_risks: list[VerdictCriticalRisk],
) -> None:
    role_set = set(roles)
    if verdict_type == VerdictKind.GO:
        if BusinessVerdictEvidenceRole.SUPPORTS not in role_set:
            raise InvalidStateError("insufficient_evidence")
        if missing_critical > 0 or conflicting_critical > 0:
            raise InvalidStateError("unresolved_critical_evidence")
        if any(r.verdict_sensitivity == VerdictSensitivity.VERDICT_CHANGING for r in critical_risks):
            raise InvalidStateError("verdict_type_not_allowed")
    elif verdict_type == VerdictKind.CONDITIONAL_GO:
        if not conditions:
            raise InvalidStateError("verdict_type_not_allowed")
        for c in conditions:
            if c.status == VerdictConditionStatus.WAIVED and not (c.waiver_note or "").strip():
                raise InvalidStateError("verdict_type_not_allowed")
        has_basis = (
            BusinessVerdictEvidenceRole.CONDITION_BASIS in role_set
            or BusinessVerdictEvidenceRole.SUPPORTS in role_set
            or missing_critical > 0
        )
        if not has_basis:
            raise InvalidStateError("insufficient_evidence")
    elif verdict_type == VerdictKind.NO_GO:
        has_neg = role_set & {
            BusinessVerdictEvidenceRole.WEAKENS,
            BusinessVerdictEvidenceRole.CONTRADICTS,
            BusinessVerdictEvidenceRole.RISK_BASIS,
        }
        if not has_neg and not critical_risks:
            raise InvalidStateError("insufficient_evidence")
    elif verdict_type == VerdictKind.INSUFFICIENT_DATA:
        # Abstention is always allowed; roles/gaps are preferred when available.
        return


def validate_go_confidence(confidence: BusinessVerdictConfidenceLevel, verdict_type: VerdictKind) -> None:
    if verdict_type == VerdictKind.GO and confidence == BusinessVerdictConfidenceLevel.LOW:
        raise InvalidStateError("verdict_type_not_allowed")


def investigation_allows_go(status: InvestigationStatus) -> bool:
    return status in (InvestigationStatus.UNDER_REVIEW, InvestigationStatus.COMPLETED)


def recommend_deterministic_verdict_type(
    *,
    readiness: VerdictReadinessStatus,
    investigation_status: InvestigationStatus,
    missing_critical: int,
    conflicting_critical: int,
    outdated_critical: int,
    accepted_count: int,
    area_coverage: dict[str, int],
    has_supporting_accepted: bool,
    has_weakening: bool,
    has_verdict_changing_risk: bool,
) -> VerdictKind:
    """Explicit deterministic draft suggestion — not readiness→GO."""

    if readiness == VerdictReadinessStatus.NOT_READY:
        return VerdictKind.INSUFFICIENT_DATA
    if missing_critical > 0 or conflicting_critical > 0:
        if readiness == VerdictReadinessStatus.CONDITIONALLY_READY:
            return VerdictKind.CONDITIONAL_GO if accepted_count > 0 else VerdictKind.INSUFFICIENT_DATA
        return VerdictKind.INSUFFICIENT_DATA
    if has_weakening and not has_supporting_accepted:
        return VerdictKind.NO_GO
    if has_verdict_changing_risk:
        return VerdictKind.CONDITIONAL_GO if readiness != VerdictReadinessStatus.NOT_READY else VerdictKind.INSUFFICIENT_DATA
    if outdated_critical > 0 or readiness == VerdictReadinessStatus.CONDITIONALLY_READY:
        return VerdictKind.CONDITIONAL_GO if accepted_count > 0 else VerdictKind.INSUFFICIENT_DATA
    if (
        readiness == VerdictReadinessStatus.READY_FOR_REVIEW
        and investigation_allows_go(investigation_status)
        and has_supporting_accepted
        and has_area_coverage(
            area_coverage,
            "market_research",
            "audience_analysis",
            "economics",
        )
        and missing_critical == 0
        and conflicting_critical == 0
        and not has_verdict_changing_risk
    ):
        return VerdictKind.GO
    if has_supporting_accepted and accepted_count > 0:
        return VerdictKind.CONDITIONAL_GO
    return VerdictKind.INSUFFICIENT_DATA


def recommend_confidence(
    *,
    readiness: VerdictReadinessStatus,
    missing_critical: int,
    conflicting_critical: int,
    outdated_critical: int,
    accepted_count: int,
) -> BusinessVerdictConfidenceLevel:
    if conflicting_critical > 0 or missing_critical > 2:
        return BusinessVerdictConfidenceLevel.LOW
    if readiness == VerdictReadinessStatus.NOT_READY or accepted_count == 0:
        return BusinessVerdictConfidenceLevel.UNKNOWN
    if outdated_critical > 0 or missing_critical > 0 or readiness == VerdictReadinessStatus.CONDITIONALLY_READY:
        return BusinessVerdictConfidenceLevel.MEDIUM
    if readiness == VerdictReadinessStatus.READY_FOR_REVIEW and accepted_count >= 3:
        return BusinessVerdictConfidenceLevel.HIGH
    return BusinessVerdictConfidenceLevel.MEDIUM
