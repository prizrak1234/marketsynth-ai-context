"""Derived capability readiness — never collapses to one boolean."""

from __future__ import annotations

from typing import Any

from app.knowledge.capability_model.catalog import resolve_skill_exists


def derive_readiness(
    capability: dict[str, Any],
    *,
    skill_bindings: list[dict[str, Any]],
) -> dict[str, bool | list[str]]:
    cap_id = capability["capability_id"]
    bound_skills = [
        b for b in skill_bindings if b.get("capability_id") == cap_id and b.get("status") == "bound"
    ]
    has_skill_package = any(resolve_skill_exists(b["skill_id"]) for b in bound_skills)
    req_patterns = capability.get("required_pattern_ids") or []
    opt_patterns = capability.get("optional_pattern_ids") or []
    has_patterns = bool(req_patterns or opt_patterns)
    has_connector_class = bool(capability.get("required_connector_classes"))
    has_tool_class = bool(capability.get("required_tool_classes"))
    needs_approval = bool(capability.get("approval_requirements"))

    readiness_findings = list(capability.get("readiness") or [])
    approval_reqs = capability.get("approval_requirements") or []
    result = {
        "methodology_exists": capability.get("implementation_status") != "deferred",
        "package_exists": has_skill_package,
        "pattern_exists": has_patterns,
        "connector_exists": False,
        "tool_exists": False,
        "runtime_exists": False,
        "approval_exists": not needs_approval or "human_approval" in approval_reqs,
        "production_release_exists": False,
        "available_as_knowledge": (
            "available_as_knowledge" in readiness_findings or has_skill_package
        ),
        "package_contract_ready": (
            "package_contract_ready" in readiness_findings or has_skill_package
        ),
        "runtime_available": False,
        "production_available": False,
        "connector_not_available": has_connector_class,
        "approval_boundary_missing": (
            needs_approval and "human_approval" not in approval_reqs
        ),
        "readiness_findings": readiness_findings,
    }
    if has_connector_class:
        result["connector_not_available"] = True
    if has_tool_class:
        result["tool_exists"] = False
    if capability.get("implementation_status") == "implemented_non_executable":
        result["runtime_available"] = False
    return result


def validate_readiness_distinction(readiness: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if readiness.get("runtime_available") and not readiness.get("package_exists"):
        errors.append("runtime_without_package")
    if readiness.get("production_available") and not readiness.get("package_contract_ready"):
        errors.append("production_without_package")
    if readiness.get("production_available") and readiness.get("runtime_available") is not True:
        pass  # expected false in this phase
    collapsed = readiness.get("ready")
    if collapsed is not None:
        errors.append("readiness_collapsed_to_boolean")
    return errors
