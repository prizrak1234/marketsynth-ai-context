"""KB-WPL-01.7 — Profession / Capability / Skill / Pattern mapping tests."""

from __future__ import annotations

import ast
from pathlib import Path

from app.knowledge.capability_model.bindings import (
    validate_capability_skill_binding,
    validate_connector_tool_binding,
    validate_pattern_connector_binding,
    validate_skill_pattern_binding,
)
from app.knowledge.capability_model.catalog import (
    load_catalog,
    resolve_skill_exists,
)
from app.knowledge.capability_model.contracts import (
    CANONICAL_HIERARCHY,
    CONNECTOR_CLASSES,
    FORBIDDEN_ORCHESTRATION_TERMS,
    NATIVE_TELEGRAM_BOUNDARY,
    PROFESSION_IDS,
    TOOL_CLASSES,
)
from app.knowledge.capability_model.dependencies import (
    build_dependency_graph,
    detect_cycle,
    validate_engineering_path,
    validate_knowledge_path,
    validate_marketing_golden_path,
)
from app.knowledge.capability_model.readiness import (
    derive_readiness,
    validate_readiness_distinction,
)
from app.knowledge.capability_model.serialization import (
    FROZEN_CAPABILITY_MODEL_BUNDLE_HASH,
    FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH,
    compute_semantic_bundle_hash,
    load_capabilities,
    load_capability_dependencies,
    load_capability_gaps,
    load_capability_skill_bindings,
    load_connector_tool_bindings,
    load_freeze_manifest,
    load_pattern_connector_bindings,
    load_professions,
    load_skill_pattern_bindings,
    recompute_freeze_manifest_bundle_hash,
)
from app.knowledge.capability_model.validation import (
    validate_bundle,
    validate_claim_before_offer,
    validate_future_skill_marked,
    validate_market_validation_before_positioning,
    validate_positioning_does_not_replace_cim,
    validate_professional_task_route,
    validate_publication_requires_approval,
)
from app.knowledge.n8n_engineering.constants import FROZEN_LIBRARY_SEMANTIC_HASH, KNOWN_PATTERN_IDS
from app.knowledge.workflow_patterns.serialization import load_library_manifest
from app.skills.hashing import calculate_skill_package_hash
from app.skills.package_validator import validate_skill_package
from tests.support.capability_model_validation import load_freeze_manifest as load_manifest_helper
from tests.support.kb_skill_validation import (
    FROZEN_MARKETING_CLAIMS_HASH,
    FROZEN_MV_020_HASH,
    FROZEN_POSITIONING_HASH,
    KB_SKILL_PACKAGE_HASHES,
)

REPO = Path(__file__).resolve().parents[1]
CAPABILITY_MODEL_DIR = REPO / "app" / "knowledge" / "capability_model"
BUNDLE_010 = REPO / "packages" / "knowledge" / "capability_model" / "0.1.0"
PATTERN_BINDINGS = BUNDLE_010 / "pattern_connector_bindings.json"
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "socket", "mcp", "telegram_mcp")


def cap(capability_id: str) -> dict:
    return next(c for c in load_capabilities() if c["capability_id"] == capability_id)

SAMPLE_ROUTE = {
    "route_id": "route-marketing-launch-001",
    "task_summary": "Plan a governed product launch presentation.",
    "selected_profession_ids": ["profession.ai_marketing_director"],
    "required_capability_ids": [
        "marketing.product_context",
        "marketing.market_validation",
        "marketing.positioning",
        "marketing.presentation_architecture",
    ],
    "candidate_skill_ids": ["ms.skill.presentation_architecture"],
    "candidate_pattern_ids": ["source_lineage_preservation", "quality_gate_after_generation"],
    "required_connector_classes": [],
    "required_tool_classes": [],
    "capability_gaps": ["gap-runtime-global"],
    "blockers": ["No publication connector activated."],
    "approval_requirements": ["human_approval"],
    "evidence_requirements": ["source_reference"],
    "route_explanation": "Read-only conceptual route for Discovery phase.",
    "human_review_required": True,
    "runtime_authorized": False,
    "provenance": {"origin": "platform_native", "phase": "KB-WPL-01.7"},
}


def test_01_canonical_hierarchy_exists() -> None:
    assert len(CANONICAL_HIERARCHY) == 6
    assert CANONICAL_HIERARCHY[0] == "Profession"
    assert CANONICAL_HIERARCHY[-1] == "Tool"


def test_02_four_professions_exist() -> None:
    assert len(load_professions()) == 4


def test_03_profession_ids_unique() -> None:
    ids = [p["profession_id"] for p in load_professions()]
    assert len(ids) == len(set(ids))


def test_04_capability_ids_unique() -> None:
    ids = [c["capability_id"] for c in load_capabilities()]
    assert len(ids) == len(set(ids))


def test_05_every_profession_capability_resolves() -> None:
    cap_ids = {c["capability_id"] for c in load_capabilities()}
    for profession in load_professions():
        for cap_id in profession["capability_ids"]:
            assert cap_id in cap_ids


def test_06_every_actual_skill_binding_resolves() -> None:
    for binding in load_capability_skill_bindings():
        if binding.get("status") != "bound":
            continue
        assert resolve_skill_exists(binding["skill_id"]), binding["skill_id"]


def test_07_missing_future_skill_marked_as_gap() -> None:
    deferred = {
        c["capability_id"]
        for c in load_capabilities()
        if c["implementation_status"] == "deferred"
    }
    gap_caps = {g["capability_id"] for g in load_capability_gaps()}
    assert deferred.intersection(gap_caps)


def test_08_every_pattern_binding_resolves_to_frozen_library() -> None:
    pattern_ids = {b["pattern_id"] for b in load_skill_pattern_bindings()}
    assert pattern_ids == set(KNOWN_PATTERN_IDS)


def test_09_unknown_pattern_rejected() -> None:
    err = validate_skill_pattern_binding(
        {"pattern_id": "unknown_pattern", "capability_id": "marketing.market_research"}
    )
    assert any("unknown_pattern" in e for e in err)


def test_10_unknown_skill_rejected_unless_deferred() -> None:
    binding = {
        "capability_id": "marketing.copywriting",
        "skill_id": "ms.skill.nonexistent",
        "status": "bound",
    }
    assert validate_capability_skill_binding(binding)
    deferred = {**binding, "status": "deferred"}
    assert not validate_capability_skill_binding(deferred)


def test_11_workflow_pattern_does_not_grant_tool_permission() -> None:
    for binding in load_skill_pattern_bindings():
        assert validate_skill_pattern_binding(binding) == []


def test_12_connector_binding_does_not_activate_connector() -> None:
    for binding in load_pattern_connector_bindings():
        assert binding.get("activates_connector") is False
        assert validate_pattern_connector_binding(binding) == []


def test_13_tool_binding_does_not_create_allowlist() -> None:
    for binding in load_connector_tool_bindings():
        assert binding.get("allowlist_mutation") is False
        assert validate_connector_tool_binding(binding) == []


def test_14_marketing_golden_path_valid() -> None:
    assert validate_marketing_golden_path(load_capability_dependencies()) == []


def test_15_market_validation_precedes_positioning() -> None:
    assert validate_market_validation_before_positioning(load_capability_dependencies()) == []


def test_16_positioning_does_not_replace_cim() -> None:
    assert validate_positioning_does_not_replace_cim(load_capability_dependencies()) == []
    positioning = cap("marketing.positioning")
    assert any("CIM" in item for item in positioning.get("limitations") or [])


def test_17_claim_substantiation_precedes_offer() -> None:
    assert validate_claim_before_offer(load_capability_dependencies()) == []


def test_18_publication_requires_approval() -> None:
    assert validate_publication_requires_approval(load_capabilities()) == []


def test_19_learning_produces_candidate_only() -> None:
    learning = cap("marketing.learning_and_feedback")
    assert learning["implementation_status"] == "deferred"
    assert "customer_feedback_to_learning_candidate" in learning["required_pattern_ids"]


def test_20_engineering_path_valid() -> None:
    assert validate_engineering_path(load_capability_dependencies()) == []


def test_21_deployment_review_precedes_future_activation() -> None:
    deps = load_capability_dependencies()
    present = {(d["source_capability_id"], d["target_capability_id"]) for d in deps}
    assert ("engineering.workflow_architecture", "engineering.deployment_review") in present


def test_22_knowledge_path_valid() -> None:
    assert validate_knowledge_path(load_capability_dependencies()) == []


def test_23_linking_precedes_persistence_recommendations() -> None:
    deps = load_capability_dependencies()
    present = {(d["source_capability_id"], d["target_capability_id"]) for d in deps}
    assert ("knowledge.knowledge_linking", "knowledge.knowledge_candidate_review") in present


def test_24_capability_readiness_distinguishes_layers() -> None:
    cap = next(c for c in load_capabilities() if c["capability_id"] == "marketing.market_research")
    readiness = derive_readiness(cap, skill_bindings=load_capability_skill_bindings())
    assert readiness["package_exists"] is True
    assert readiness["runtime_available"] is False
    assert readiness["production_available"] is False
    assert validate_readiness_distinction(readiness) == []


def test_25_missing_runtime_visible() -> None:
    gaps = load_capability_gaps()
    assert any(g.get("missing_runtime") for g in gaps)


def test_26_missing_connector_visible() -> None:
    gaps = load_capability_gaps()
    assert any(g.get("missing_connector_classes") for g in gaps)


def test_27_missing_approval_blocks_publication_capability() -> None:
    distribution = cap("marketing.distribution")
    assert "human_approval" in distribution["approval_requirements"]
    assert "approval_boundary_missing" in distribution["readiness"]


def test_28_future_capability_not_marked_implemented() -> None:
    for cap in load_capabilities():
        if cap["capability_id"] == "marketing.content_strategy":
            assert cap["implementation_status"] == "deferred"
            break


def test_29_pattern_only_capability_not_runtime_ready() -> None:
    selected = cap("engineering.pattern_selection")
    readiness = derive_readiness(selected, skill_bindings=load_capability_skill_bindings())
    assert readiness["runtime_available"] is False


def test_30_profession_runtime_authorized_false() -> None:
    for profession in load_professions():
        assert profession["runtime_authorized"] is False


def test_31_task_route_runtime_authorized_false() -> None:
    assert validate_professional_task_route(SAMPLE_ROUTE) == []


def test_32_no_autonomous_orchestration() -> None:
    assert validate_professional_task_route({**SAMPLE_ROUTE, "autonomous_orchestration": True})


def test_33_no_external_employee_runtime() -> None:
    for term in FORBIDDEN_ORCHESTRATION_TERMS:
        assert term not in str(load_professions())


def test_34_no_connector_activation() -> None:
    manifest = load_freeze_manifest()
    assert manifest["runtime_authorized"] is False


def test_35_no_telegram_mcp() -> None:
    binding_text = PATTERN_BINDINGS.read_text(encoding="utf-8")
    assert "telegram_mcp" not in binding_text.lower()


def test_36_native_telegram_boundary_preserved() -> None:
    assert "Telegram" in NATIVE_TELEGRAM_BOUNDARY


def test_37_gaps_deterministic() -> None:
    gaps_a = load_capability_gaps()
    gaps_b = load_capability_gaps()
    assert gaps_a == gaps_b


def test_38_capability_graph_acyclic_where_required() -> None:
    deps = load_capability_dependencies()
    required_edges = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in deps
        if d.get("dependency_type") == "required"
    }
    graph = build_dependency_graph(deps)
    assert not detect_cycle(graph, required_edges=required_edges)


def test_39_optional_dependencies_no_false_cycle() -> None:
    deps = load_capability_dependencies()
    required_edges = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in deps
        if d.get("dependency_type") == "required"
    }
    graph = build_dependency_graph(deps)
    optional_only = {
        (d["source_capability_id"], d["target_capability_id"])
        for d in deps
        if d.get("dependency_type") == "optional"
    }
    assert not detect_cycle(graph, required_edges=required_edges)
    assert optional_only


def test_40_bundle_hash_deterministic() -> None:
    manifest = load_freeze_manifest()
    assert manifest["bundle_hash"] == recompute_freeze_manifest_bundle_hash()
    assert manifest["bundle_hash"] == FROZEN_CAPABILITY_MODEL_BUNDLE_HASH


def test_41_generated_at_excluded_from_semantic_hash() -> None:
    semantic = compute_semantic_bundle_hash()
    assert semantic == FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH
    manifest = load_freeze_manifest()
    assert manifest["semantic_bundle_hash"] == semantic


def test_42_registry_audit_lineage_references_preserved() -> None:
    report = validate_skill_package(REPO / "packages" / "skills" / "ms.skill.knowledge_linking")
    from app.lineage.builders import build_package_validation_lineage

    lineage = build_package_validation_lineage(report)
    assert lineage.nodes


def test_43_frozen_wpl_hash_unchanged() -> None:
    manifest = load_library_manifest()
    assert manifest["library_semantic_hash"] == FROZEN_LIBRARY_SEMANTIC_HASH


def test_44_frozen_marketing_skill_hashes_unchanged() -> None:
    positioning_root = REPO / "packages" / "skills" / "ms.skill.positioning"
    mv_root = REPO / "packages" / "skills" / "ms.skill.market_validation" / "0.2.0"
    assert calculate_skill_package_hash(positioning_root) == FROZEN_POSITIONING_HASH
    assert calculate_skill_package_hash(mv_root) == FROZEN_MV_020_HASH


def test_45_frozen_engineering_skill_hashes_unchanged() -> None:
    for skill_id, expected in KB_SKILL_PACKAGE_HASHES.items():
        if "n8n" in skill_id:
            root = REPO / "packages" / "skills" / skill_id
            assert calculate_skill_package_hash(root) == expected


def test_46_frozen_knowledge_linking_hash_unchanged() -> None:
    root = REPO / "packages" / "skills" / "ms.skill.knowledge_linking"
    linking_hash = KB_SKILL_PACKAGE_HASHES["ms.skill.knowledge_linking"]
    assert calculate_skill_package_hash(root) == linking_hash


def test_47_frozen_presentation_architecture_hash_unchanged() -> None:
    root = REPO / "packages" / "skills" / "ms.skill.presentation_architecture"
    pres_hash = KB_SKILL_PACKAGE_HASHES["ms.skill.presentation_architecture"]
    assert calculate_skill_package_hash(root) == pres_hash


def test_48_no_persistence_api_ui_network_mcp() -> None:
    for path in CAPABILITY_MODEL_DIR.glob("**/*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN_IMPORTS, alias.name
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS, node.module


def test_49_existing_kb_wpl_tests_remain_green() -> None:
    assert validate_bundle() == []
    catalog = load_catalog()
    assert len(catalog["known_skill_ids"]) >= 15


def test_50_all_profession_ids_canonical() -> None:
    assert {p["profession_id"] for p in load_professions()} == set(PROFESSION_IDS)


def test_connector_and_tool_classes_conceptual() -> None:
    assert CONNECTOR_CLASSES
    assert TOOL_CLASSES
    assert "publication_connector" in CONNECTOR_CLASSES
    assert "publish" in TOOL_CLASSES


def test_cim_shared_contract_on_customer_intelligence() -> None:
    customer_intel = cap("marketing.customer_intelligence")
    cim_ref = "packages/knowledge/customer_intelligence/0.1.0"
    assert cim_ref in customer_intel.get("shared_contract_references", [])


def test_marketing_claims_bundle_unchanged() -> None:
    from tests.support.kb_skill_validation import load_external_artifacts_manifest

    _ = load_external_artifacts_manifest()
    claims_path = REPO / "packages" / "knowledge" / "marketing_claims" / "0.1.0"
    claims_manifest = claims_path / "freeze_manifest.json"
    if claims_manifest.is_file():
        import json

        data = json.loads(claims_manifest.read_text(encoding="utf-8"))
        assert data.get("bundle_hash") == FROZEN_MARKETING_CLAIMS_HASH


def test_future_skill_binding_helper() -> None:
    assert validate_future_skill_marked({"status": "deferred", "skill_id": "ms.skill.copywriting"})


def test_manifest_helper_loads() -> None:
    assert load_manifest_helper()["bundle_status"] == "mapped_read_only_model"
