"""ImplementationPlan → MarketingPlan draft mapping (Commercial MVP P1.2).

Mapping version: implementation_to_marketing_plan.v1
Does not approve, dispatch, or create Agent Runs / Campaigns.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.exceptions import InvalidStateError
from app.db.models.implementation_plan import ImplementationPlanTable
from app.schemas.contracts import (
    HandoffTaskClassification,
    HandoffTaskMappingItem,
    ImplementationPlanLifecycleStatus,
    ImplementationPlanReadinessStatus,
    ImplLocalGateStatus,
    ImplTaskMappingEligibility,
    MAPPING_VERSION_V1,
    MarketingExecutionMode,
    MarketingExecutionPlan,
    MarketingSpecialistTask,
    MarketingSpecialistType,
)

# Mirrors web/src/lib/integration/role-mapping.ts — no new AgentType / specialist values.
_ROLE_TO_SPECIALIST: dict[str, MarketingSpecialistType | None] = {
    "CEO": None,
    "Client Owner": None,
    "Project Manager": None,
    "Designer": None,
    "Performance Marketer": None,
    "Research Director": MarketingSpecialistType.RESEARCHER,
    "Market Analyst": MarketingSpecialistType.ANALYST,
    "Competitor Analyst": MarketingSpecialistType.RESEARCHER,
    "Audience Analyst": MarketingSpecialistType.RESEARCHER,
    "Risk Officer": MarketingSpecialistType.CRITIC,
    "Chief Marketing Strategist": MarketingSpecialistType.STRATEGIST,
    "Content Strategist": MarketingSpecialistType.CONTENT_PLANNER,
    "Copywriter": MarketingSpecialistType.COPYWRITER,
    "Analyst": MarketingSpecialistType.ANALYST,
}

_CRITICAL_DEP_KEYWORDS = (
    "legal",
    "compliance",
    "budget",
    "publication",
    "publish",
    "paid",
    "evidence",
    "validation",
    "offer final",
)


def assert_plan_eligible_for_confirm(plan: ImplementationPlanTable) -> None:
    status = ImplementationPlanLifecycleStatus(plan.lifecycle_status)
    if status != ImplementationPlanLifecycleStatus.APPROVED:
        raise InvalidStateError("implementation_plan_not_approved")
    readiness = ImplementationPlanReadinessStatus(plan.readiness_status)
    if readiness != ImplementationPlanReadinessStatus.READY_FOR_HANDOFF:
        raise InvalidStateError("readiness_not_ready_for_handoff")


def assert_plan_previewable(plan: ImplementationPlanTable) -> None:
    status = ImplementationPlanLifecycleStatus(plan.lifecycle_status)
    if status in (
        ImplementationPlanLifecycleStatus.REJECTED,
        ImplementationPlanLifecycleStatus.ARCHIVED,
        ImplementationPlanLifecycleStatus.SUPERSEDED,
    ):
        raise InvalidStateError("implementation_plan_not_approved")


def map_role(role: str) -> MarketingSpecialistType | None:
    return _ROLE_TO_SPECIALIST.get(role)


def _task_dict(raw: Any) -> dict[str, Any]:
    if hasattr(raw, "model_dump"):
        return raw.model_dump(mode="json")
    return dict(raw)


def classify_and_map_tasks(
    plan: ImplementationPlanTable,
) -> tuple[
    list[HandoffTaskMappingItem],
    list[HandoffTaskMappingItem],
    list[HandoffTaskMappingItem],
    list[HandoffTaskMappingItem],
    list[HandoffTaskMappingItem],
    list[str],
    list[str],
    list[str],
    list[str],
]:
    included: list[HandoffTaskMappingItem] = []
    transformed: list[HandoffTaskMappingItem] = []
    excluded: list[HandoffTaskMappingItem] = []
    unsupported: list[HandoffTaskMappingItem] = []
    blocked: list[HandoffTaskMappingItem] = []
    role_notes: list[str] = []
    dep_warnings: list[str] = []
    ac_warnings: list[str] = []
    gate_blockers: list[str] = []

    open_condition_ids: set[str] = set()
    for c in plan.conditions or []:
        data = c if isinstance(c, dict) else dict(c)
        status = str(data.get("current_status_snapshot") or "open")
        if status in ("open", "in_progress", "failed"):
            open_condition_ids.add(str(data.get("id") or ""))
            for tid in data.get("blocking_task_ids") or []:
                open_condition_ids.add(f"task:{tid}")

    pending_critical_gates: list[str] = []
    for g in list(plan.budget_gates or []) + list(plan.approval_gates or []):
        data = g if isinstance(g, dict) else dict(g)
        st = str(data.get("lifecycle_status") or "")
        if st == ImplLocalGateStatus.PENDING.value:
            title = str(data.get("title") or data.get("id") or "gate")
            pending_critical_gates.append(title)
            gate_blockers.append(f"pending_gate:{title}")

    deps = plan.dependencies or []
    if deps:
        dep_warnings.append(
            "MarketingPlan specialist_tasks do not support dependency graph; "
            "dependencies preserved only in handoff snapshot (degraded)."
        )

    for raw in plan.tasks or []:
        t = _task_dict(raw)
        tid = str(t.get("id") or "")
        title = str(t.get("title") or tid)
        role = str(t.get("responsible_role") or "")
        eligibility = str(
            t.get("mapping_eligibility") or ImplTaskMappingEligibility.TRANSFORMABLE.value
        )
        specialist = map_role(role)
        criteria = t.get("acceptance_criteria") or []
        dep_ids = t.get("dependency_ids") or []
        obj_parts = [str(t.get("description") or "").strip(), title]
        objective = " — ".join([p for p in obj_parts if p])[:4000] or title
        expected = str(t.get("expected_output") or "").strip()
        ac_mode = "none"
        if criteria:
            expected = (
                (expected + "\n\nAcceptance criteria:\n- " + "\n- ".join(str(c) for c in criteria))
                if expected
                else ("Acceptance criteria:\n- " + "\n- ".join(str(c) for c in criteria))
            )[:4000]
            ac_mode = "degraded_into_expected_output"
            ac_warnings.append(
                f"task:{tid}: acceptance criteria folded into expected_output (no first-class field)"
            )

        dep_mode = "none"
        if dep_ids or deps:
            dep_mode = "degraded_warning"
            blob = (title + " " + objective + " " + " ".join(str(d) for d in dep_ids)).lower()
            if any(k in blob for k in ("budget", "paid", "legal", "compliance", "publish")):
                dep_mode = "blocking_loss"

        item = HandoffTaskMappingItem(
            implementation_task_id=tid,
            title=title,
            classification=HandoffTaskClassification.TRANSFORMABLE,
            reason="",
            mapped_specialist=specialist,
            mapped_objective=objective,
            mapped_expected_output=expected or "Defined during MarketingPlan review",
            acceptance_criteria_mode=ac_mode,
            dependency_mode=dep_mode,
            responsible_role=role,
        )

        if eligibility == ImplTaskMappingEligibility.EXCLUDED.value:
            item.classification = HandoffTaskClassification.EXCLUDED
            item.reason = "Marked excluded on ImplementationPlan"
            item.mapped_specialist = None
            excluded.append(item)
            continue

        if specialist is None:
            item.classification = HandoffTaskClassification.UNSUPPORTED
            item.reason = f"Role '{role}' has no executable MarketingSpecialistType"
            item.mapped_specialist = None
            unsupported.append(item)
            role_notes.append(f"{role} → unsupported")
            continue

        role_notes.append(f"{role} → {specialist.value}")

        blocked_reason = str(t.get("blocked_reason") or "")
        if eligibility == ImplTaskMappingEligibility.BLOCKED.value or blocked_reason:
            item.classification = HandoffTaskClassification.BLOCKED
            item.reason = blocked_reason or "Task marked blocked"
            blocked.append(item)
            continue

        if f"task:{tid}" in open_condition_ids or any(
            tid in str(x) for x in open_condition_ids
        ):
            item.classification = HandoffTaskClassification.BLOCKED
            item.reason = "Unresolved Verdict/Strategy condition blocks conversion"
            blocked.append(item)
            continue

        if dep_mode == "blocking_loss":
            item.classification = HandoffTaskClassification.BLOCKED
            item.reason = "Critical dependency cannot be represented on MarketingPlan spine"
            blocked.append(item)
            continue

        if t.get("approval_required") and pending_critical_gates and "channel" in title.lower():
            item.classification = HandoffTaskClassification.BLOCKED
            item.reason = "Pending budget/approval gate blocks acquisition conversion"
            blocked.append(item)
            continue

        if eligibility == ImplTaskMappingEligibility.EXACT.value and ac_mode in (
            "none",
            "exact",
        ):
            item.classification = HandoffTaskClassification.EXACT
            item.reason = "Direct specialist role match"
            included.append(item)
        else:
            item.classification = HandoffTaskClassification.TRANSFORMABLE
            item.reason = "Safe role/object mapping with degraded acceptance/deps"
            transformed.append(item)

    return (
        included,
        transformed,
        excluded,
        unsupported,
        blocked,
        sorted(set(role_notes)),
        dep_warnings,
        ac_warnings,
        gate_blockers,
    )


def build_execution_plan_from_mapped(
    *,
    plan: ImplementationPlanTable,
    included: list[HandoffTaskMappingItem],
    transformed: list[HandoffTaskMappingItem],
    handoff_id: str,
    fingerprint: str,
) -> MarketingExecutionPlan:
    tasks: list[MarketingSpecialistTask] = []
    for item in included + transformed:
        if item.mapped_specialist is None:
            continue
        tasks.append(
            MarketingSpecialistTask(
                specialist=item.mapped_specialist,
                objective=item.mapped_objective or item.title,
                expected_output=item.mapped_expected_output or "Review output",
            )
        )
    if not tasks:
        raise InvalidStateError("marketing_plan_create_unsafe")

    context = {
        "source": "commercial_mvp_p1_2_handoff",
        "mapping_version": MAPPING_VERSION_V1,
        "mapping_fingerprint": fingerprint,
        "handoff_id": handoff_id,
        "source_implementation_plan_id": str(plan.id),
        "source_implementation_plan_version": plan.version,
        "source_marketing_strategy_id": str(plan.marketing_strategy_id),
        "source_business_verdict_id": str(plan.business_verdict_id),
        "source_evidence_snapshot_hash": plan.evidence_snapshot_hash,
        "creates_agent_run": False,
        "auto_approve": False,
        "dispatches_specialist_tasks": False,
    }
    return MarketingExecutionPlan(
        goal=(plan.summary or plan.title)[:4000],
        project_context=context,
        specialist_tasks=tasks,
        execution_mode=MarketingExecutionMode.PLANNING,
    )


def compute_mapping_fingerprint(
    *,
    plan_id: str,
    plan_version: int,
    mapping_version: str,
    policy: str,
    mapped_payload: list[dict[str, Any]],
) -> str:
    canonical = {
        "plan_id": plan_id,
        "plan_version": plan_version,
        "mapping_version": mapping_version,
        "policy": policy,
        "tasks": sorted(mapped_payload, key=lambda x: x.get("implementation_task_id", "")),
    }
    raw = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def mapped_payload_for_fingerprint(
    included: list[HandoffTaskMappingItem],
    transformed: list[HandoffTaskMappingItem],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in included + transformed:
        out.append(
            {
                "implementation_task_id": item.implementation_task_id,
                "specialist": item.mapped_specialist.value if item.mapped_specialist else None,
                "objective": item.mapped_objective,
                "expected_output": item.mapped_expected_output,
                "classification": item.classification.value,
            }
        )
    return out


def confirm_eligibility_blockers(
    plan: ImplementationPlanTable,
    *,
    included_count: int,
    blocked: list[HandoffTaskMappingItem],
    gate_blockers: list[str],
) -> list[str]:
    blockers: list[str] = []
    try:
        assert_plan_eligible_for_confirm(plan)
    except InvalidStateError as exc:
        blockers.append(str(exc))
    if included_count < 1:
        blockers.append("no_mappable_tasks")
    if gate_blockers and ImplementationPlanReadinessStatus(plan.readiness_status) != (
        ImplementationPlanReadinessStatus.READY_FOR_HANDOFF
    ):
        blockers.extend(gate_blockers)
    return blockers
