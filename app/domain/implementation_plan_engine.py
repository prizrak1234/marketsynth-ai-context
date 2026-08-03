"""ImplementationPlan domain rules (Commercial MVP P1.1).

ImplementationPlan ≠ MarketingPlan.
Eligible only from an exact approved MarketingStrategy version.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.core.exceptions import InvalidStateError
from app.db.models.marketing_strategy import MarketingStrategyTable
from app.schemas.contracts import (
    ImplAssumptionStatus,
    ImplDependency,
    ImplLocalGateStatus,
    ImplTask,
    ImplTaskMappingEligibility,
    ImplementationPlanHandoffPreview,
    ImplementationPlanReadinessStatus,
    MarketingStrategyLifecycleStatus,
)


def assert_strategy_allows_plan(strategy: MarketingStrategyTable) -> None:
    status = MarketingStrategyLifecycleStatus(strategy.lifecycle_status)
    if status == MarketingStrategyLifecycleStatus.SUPERSEDED:
        raise InvalidStateError("strategy_superseded")
    if status != MarketingStrategyLifecycleStatus.APPROVED:
        raise InvalidStateError("strategy_not_approved")


def detect_dependency_cycles(dependencies: list[ImplDependency] | list[dict[str, Any]]) -> None:
    graph: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for dep in dependencies:
        data = dep.model_dump() if hasattr(dep, "model_dump") else dict(dep)
        pred = f"{data['predecessor_type']}:{data['predecessor_id']}"
        succ = f"{data['successor_type']}:{data['successor_id']}"
        graph[pred].append(succ)
        nodes.add(pred)
        nodes.add(succ)

    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> None:
        if node in visiting:
            raise InvalidStateError("dependency_cycle")
        if node in visited:
            return
        visiting.add(node)
        for nxt in graph.get(node, []):
            dfs(nxt)
        visiting.remove(node)
        visited.add(node)

    for n in list(nodes):
        dfs(n)


def validate_tasks_acceptance(tasks: list[ImplTask] | list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for task in tasks:
        data = task.model_dump() if hasattr(task, "model_dump") else dict(task)
        criteria = data.get("acceptance_criteria") or []
        if not criteria:
            missing.append(str(data.get("id") or "unknown"))
    return missing


def validate_unsupported_roles(
    role_assignments: list[Any],
) -> list[str]:
    unsupported: list[str] = []
    for role in role_assignments:
        data = role.model_dump() if hasattr(role, "model_dump") else dict(role)
        if str(data.get("role_type") or "") == "unsupported":
            unsupported.append(str(data.get("implementation_role") or ""))
        if data.get("execution_mapping_allowed") and str(data.get("role_type")) == "unsupported":
            raise InvalidStateError("unsupported_role")
    return [r for r in unsupported if r]


def compute_plan_readiness(
    *,
    workstreams: list[Any],
    milestones: list[Any],
    tasks: list[Any],
    dependencies: list[Any],
    deliverables: list[Any],
    budget_gates: list[Any],
    approval_gates: list[Any],
    conditions: list[Any],
    assumptions: list[Any],
    implementation_risks: list[Any],
    role_assignments: list[Any],
) -> tuple[ImplementationPlanReadinessStatus, list[str]]:
    reasons: list[str] = []

    if not workstreams:
        reasons.append("missing_workstreams")
    if not milestones:
        reasons.append("missing_milestones")
    if not tasks:
        reasons.append("missing_tasks")
    if not deliverables:
        reasons.append("missing_deliverables")
    if not role_assignments:
        reasons.append("missing_role_assignments")
    if not approval_gates:
        reasons.append("missing_approval_gates")

    missing_ac = validate_tasks_acceptance(tasks)
    if missing_ac:
        reasons.append("missing_acceptance_criteria")

    try:
        detect_dependency_cycles(dependencies)
    except InvalidStateError:
        reasons.append("dependency_cycle")

    for a in assumptions:
        data = a.model_dump() if hasattr(a, "model_dump") else dict(a)
        if str(data.get("lifecycle_status") or "") == ImplAssumptionStatus.INVALIDATED.value:
            reasons.append("invalidated_assumption")
            return ImplementationPlanReadinessStatus.BLOCKED, reasons

    blocking_conditions = False
    for c in conditions:
        data = c.model_dump() if hasattr(c, "model_dump") else dict(c)
        status = str(data.get("current_status_snapshot") or "open")
        if status in ("open", "in_progress", "failed"):
            blocking_conditions = True

    critical_risks = False
    for r in implementation_risks:
        data = r.model_dump() if hasattr(r, "model_dump") else dict(r)
        if str(data.get("severity") or "") == "critical" and str(
            data.get("lifecycle_status") or "open"
        ) == "open":
            critical_risks = True

    unsupported = validate_unsupported_roles(role_assignments)
    if unsupported:
        reasons.append("unsupported_role_mappings")

    pending_budget = any(
        str(
            (g.model_dump() if hasattr(g, "model_dump") else dict(g)).get("lifecycle_status")
            or ""
        )
        == ImplLocalGateStatus.PENDING.value
        for g in budget_gates
    )

    if "dependency_cycle" in reasons or "missing_acceptance_criteria" in reasons:
        return ImplementationPlanReadinessStatus.BLOCKED, reasons
    if reasons:
        return ImplementationPlanReadinessStatus.NOT_READY, reasons
    if blocking_conditions or critical_risks or pending_budget or unsupported:
        if pending_budget:
            reasons.append("pending_budget_gates")
        if blocking_conditions:
            reasons.append("open_conditions")
        if critical_risks:
            reasons.append("open_critical_risks")
        return ImplementationPlanReadinessStatus.CONDITIONALLY_READY, reasons
    return ImplementationPlanReadinessStatus.READY_FOR_HANDOFF, ["eligible_for_handoff_preview"]


def build_handoff_preview(
    *,
    plan_id: Any,
    plan_version: int,
    readiness: ImplementationPlanReadinessStatus,
    readiness_reasons: list[str],
    tasks: list[Any],
    role_assignments: list[Any],
    dependencies: list[Any],
    budget_gates: list[Any],
    approval_gates: list[Any],
) -> ImplementationPlanHandoffPreview:
    mapped = unsupported = blocked = 0
    for t in tasks:
        data = t.model_dump() if hasattr(t, "model_dump") else dict(t)
        elig = str(data.get("mapping_eligibility") or "")
        if elig == ImplTaskMappingEligibility.EXACT.value:
            mapped += 1
        elif elig in (
            ImplTaskMappingEligibility.UNSUPPORTED.value,
            ImplTaskMappingEligibility.EXCLUDED.value,
        ):
            unsupported += 1
        elif elig == ImplTaskMappingEligibility.BLOCKED.value:
            blocked += 1
        else:
            mapped += 1  # transformable counts toward potential map

    unsupported_roles = validate_unsupported_roles(role_assignments)
    dep_loss: list[str] = []
    if dependencies:
        dep_loss.append(
            "Dependency graph not automatically transferable to MarketingPlan in P1.1"
        )
    ac_loss = [
        f"task:{tid}" for tid in validate_tasks_acceptance(tasks)
    ]
    budget_gaps = [
        str((g.model_dump() if hasattr(g, "model_dump") else dict(g)).get("id") or "")
        for g in budget_gates
        if str(
            (g.model_dump() if hasattr(g, "model_dump") else dict(g)).get("lifecycle_status")
            or ""
        )
        == ImplLocalGateStatus.PENDING.value
    ]
    approval_gaps = [
        str((g.model_dump() if hasattr(g, "model_dump") else dict(g)).get("id") or "")
        for g in approval_gates
        if str(
            (g.model_dump() if hasattr(g, "model_dump") else dict(g)).get("lifecycle_status")
            or ""
        )
        == ImplLocalGateStatus.PENDING.value
    ]
    blockers = list(readiness_reasons)
    if unsupported_roles:
        blockers.append("unsupported_roles")
    eligible = readiness == ImplementationPlanReadinessStatus.READY_FOR_HANDOFF and not blockers
    # Conditionally ready can still preview, but not eligible to create in future P1.2 without confirmation
    if readiness == ImplementationPlanReadinessStatus.CONDITIONALLY_READY:
        eligible = False
    if readiness == ImplementationPlanReadinessStatus.READY_FOR_HANDOFF:
        eligible = True
        blockers = []

    return ImplementationPlanHandoffPreview(
        plan_id=plan_id,
        plan_version=plan_version,
        eligible=eligible,
        mapped_task_count=mapped,
        unsupported_task_count=unsupported,
        blocked_task_count=blocked,
        unsupported_roles=unsupported_roles,
        dependency_loss=dep_loss,
        acceptance_criteria_loss=ac_loss,
        budget_gate_gaps=[x for x in budget_gaps if x],
        approval_gate_gaps=[x for x in approval_gaps if x],
        readiness=readiness,
        blockers=blockers,
        creates_marketing_plan=False,
        creates_specialist_tasks=False,
    )
