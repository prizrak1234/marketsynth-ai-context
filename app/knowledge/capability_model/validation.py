"""Semantic validation for KB-WPL-01.7 capability mapping."""

from __future__ import annotations

from typing import Any

from app.knowledge.capability_model.bindings import (
    validate_capability_skill_binding,
    validate_connector_tool_binding,
    validate_pattern_connector_binding,
    validate_skill_pattern_binding,
)
from app.knowledge.capability_model.catalog import (
    capability_index,
    profession_index,
    resolve_skill_exists,
)
from app.knowledge.capability_model.contracts import (
    CAPABILITY_IMPLEMENTATION_STATUSES,
    CAPABILITY_READINESS_VALUES,
    FORBIDDEN_ORCHESTRATION_TERMS,
    FORBIDDEN_RUNTIME_FIELDS,
    NATIVE_TELEGRAM_BOUNDARY,
    PROFESSION_DOMAINS,
    PROFESSION_IDS,
    PROFESSION_PRODUCTION_STATUSES,
)
from app.knowledge.capability_model.dependencies import (
    build_dependency_graph,
    detect_cycle,
    validate_engineering_path,
    validate_knowledge_path,
    validate_marketing_golden_path,
)
from app.knowledge.capability_model.gaps import validate_capability_gap
from app.knowledge.capability_model.readiness import (
    derive_readiness,
    validate_readiness_distinction,
)
from app.knowledge.capability_model.serialization import (
    load_capabilities,
    load_capability_dependencies,
    load_capability_gaps,
    load_capability_skill_bindings,
    load_connector_tool_bindings,
    load_pattern_connector_bindings,
    load_professions,
    load_skill_pattern_bindings,
)
from app.knowledge.n8n_engineering.constants import KNOWN_PATTERN_IDS


def validate_profession(profession: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in (
        "profession_id",
        "profession_name",
        "domain",
        "objective",
        "responsibilities",
        "capability_ids",
        "version",
        "provenance",
    ):
        if not profession.get(field):
            errors.append(f"missing_profession_field:{field}")
    if profession.get("domain") not in PROFESSION_DOMAINS:
        errors.append("invalid_profession_domain")
    if profession.get("production_status") not in PROFESSION_PRODUCTION_STATUSES:
        errors.append("invalid_profession_production_status")
    if profession.get("runtime_authorized") is not False:
        errors.append("profession_runtime_must_be_false")
    if profession.get("human_accountability_required") is not True:
        errors.append("profession_human_accountability_required")
    return errors


def validate_capability(capability: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in (
        "capability_id",
        "capability_name",
        "profession_ids",
        "objective",
        "implementation_status",
        "readiness",
        "provenance",
    ):
        if not capability.get(field):
            errors.append(f"missing_capability_field:{field}")
    if capability.get("implementation_status") not in CAPABILITY_IMPLEMENTATION_STATUSES:
        errors.append("invalid_implementation_status")
    readiness = capability.get("readiness") or []
    if not isinstance(readiness, list):
        errors.append("readiness_must_be_list")
    elif any(item not in CAPABILITY_READINESS_VALUES for item in readiness):
        errors.append("invalid_readiness_value")
    if capability.get("runtime_authorized") is True:
        errors.append("capability_runtime_authorized")
    return errors


def validate_professional_task_route(route: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("route_id", "task_summary", "route_explanation", "provenance"):
        if not route.get(field):
            errors.append(f"missing_route_field:{field}")
    if route.get("runtime_authorized") is not False:
        errors.append("route_runtime_must_be_false")
    for forbidden in FORBIDDEN_RUNTIME_FIELDS:
        if route.get(forbidden) is True:
            errors.append(f"forbidden_route_field:{forbidden}")
    if route.get("autonomous_orchestration"):
        errors.append("autonomous_orchestration_forbidden")
    if route.get("telegram_mcp"):
        errors.append("telegram_mcp_forbidden")
    return errors


def validate_bundle() -> list[str]:
    errors: list[str] = []
    professions = load_professions()
    capabilities = load_capabilities()
    cap_idx = capability_index(capabilities)
    prof_idx = profession_index(professions)

    if len(professions) != 4:
        errors.append("expected_four_professions")
    profession_ids = [p.get("profession_id") for p in professions]
    if len(profession_ids) != len(set(profession_ids)):
        errors.append("duplicate_profession_id")
    for pid in PROFESSION_IDS:
        if pid not in prof_idx:
            errors.append(f"missing_profession:{pid}")

    capability_ids = [c.get("capability_id") for c in capabilities]
    if len(capability_ids) != len(set(capability_ids)):
        errors.append("duplicate_capability_id")

    for profession in professions:
        errors.extend(validate_profession(profession))
        for cap_id in profession.get("capability_ids") or []:
            if cap_id not in cap_idx:
                errors.append(f"unresolved_profession_capability:{cap_id}")

    for capability in capabilities:
        errors.extend(validate_capability(capability))
        for prof_id in capability.get("profession_ids") or []:
            if prof_id not in prof_idx:
                errors.append(f"unresolved_capability_profession:{prof_id}")

    skill_bindings = load_capability_skill_bindings()
    for binding in skill_bindings:
        errors.extend(validate_capability_skill_binding(binding))
        cap_id = binding.get("capability_id")
        if cap_id and cap_id not in cap_idx:
            errors.append(f"binding_unknown_capability:{cap_id}")

    pattern_bindings = load_skill_pattern_bindings()
    for binding in pattern_bindings:
        errors.extend(validate_skill_pattern_binding(binding))

    if len({b["pattern_id"] for b in pattern_bindings}) != len(KNOWN_PATTERN_IDS):
        missing = KNOWN_PATTERN_IDS - {b["pattern_id"] for b in pattern_bindings}
        for pid in missing:
            errors.append(f"missing_pattern_binding:{pid}")

    for binding in load_pattern_connector_bindings():
        errors.extend(validate_pattern_connector_binding(binding))
    for binding in load_connector_tool_bindings():
        errors.extend(validate_connector_tool_binding(binding))

    dependencies = load_capability_dependencies()
    errors.extend(validate_marketing_golden_path(dependencies))
    errors.extend(validate_engineering_path(dependencies))
    errors.extend(validate_knowledge_path(dependencies))

    required_edges = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in dependencies
        if d.get("dependency_type") == "required"
    }
    graph = build_dependency_graph(dependencies)
    if detect_cycle(graph, required_edges=required_edges):
        errors.append("required_dependency_cycle")

    gaps = load_capability_gaps()
    for gap in gaps:
        errors.extend(validate_capability_gap(gap))

    for capability in capabilities:
        readiness = derive_readiness(capability, skill_bindings=skill_bindings)
        errors.extend(validate_readiness_distinction(readiness))

    pub_caps = [
        c
        for c in capabilities
        if "distribution" in c["capability_id"] or "publication" in c["capability_id"]
    ]
    for cap in pub_caps:
        tools = cap.get("required_tool_classes") or []
        approvals = cap.get("approval_requirements") or []
        if "publish" in tools and "human_approval" not in approvals:
            errors.append(f"publication_missing_approval:{cap['capability_id']}")

    learning = cap_idx.get("marketing.learning_and_feedback")
    if learning and learning.get("implementation_status") == "implemented_non_executable":
        errors.append("learning_marked_implemented")

    for term in FORBIDDEN_ORCHESTRATION_TERMS:
        if term in str(professions):
            errors.append(f"forbidden_hierarchy_term:{term}")

    if "telegram_mcp" in str(load_pattern_connector_bindings()):
        errors.append("telegram_mcp_in_bindings")

    _ = NATIVE_TELEGRAM_BOUNDARY  # documentation anchor for tests
    return errors


def validate_positioning_does_not_replace_cim(dependencies: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for dep in dependencies:
        if (
            dep.get("source_capability_id") == "marketing.positioning"
            and dep.get("target_capability_id") == "marketing.customer_intelligence"
            and dep.get("relationship") == "replaces"
        ):
            errors.append("positioning_replaces_cim")
    return errors


def validate_claim_before_offer(dependencies: list[dict[str, Any]]) -> list[str]:
    present = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in dependencies
        if d.get("dependency_type") == "required"
    }
    if ("marketing.claim_substantiation", "marketing.offer_architecture") not in present:
        return ["claim_substantiation_before_offer_missing"]
    return []


def validate_publication_requires_approval(capabilities: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for cap in capabilities:
        cap_id = cap["capability_id"]
        tools = cap.get("required_tool_classes") or []
        approvals = cap.get("approval_requirements") or []
        if (
            ("publication" in cap_id or cap_id == "marketing.distribution")
            and "publish" in tools
            and "human_approval" not in approvals
        ):
            errors.append(f"publication_missing_approval:{cap_id}")
    return errors


def validate_market_validation_before_positioning(dependencies: list[dict[str, Any]]) -> list[str]:
    present = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in dependencies
        if d.get("dependency_type") == "required"
    }
    if ("marketing.market_validation", "marketing.positioning") not in present:
        return ["market_validation_before_positioning_missing"]
    return []


def validate_future_skill_marked(binding: dict[str, Any]) -> bool:
    if binding.get("status") in {"deferred", "future", "specified"}:
        return True
    return resolve_skill_exists(binding.get("skill_id", ""))
