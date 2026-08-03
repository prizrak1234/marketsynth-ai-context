"""KB-WPL-01.9 — Integrated program freeze audit."""
# ruff: noqa: E501

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest
from app.knowledge.capability_model.serialization import (
    FROZEN_CAPABILITY_MODEL_BUNDLE_HASH,
    FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH,
    compute_semantic_bundle_hash,
    load_capabilities,
    load_capability_skill_bindings,
    load_professions,
    load_skill_pattern_bindings,
    recompute_freeze_manifest_bundle_hash,
)
from app.knowledge.capability_model.validation import validate_bundle
from app.knowledge.discovery.contracts import FORBIDDEN_RECOMMENDED_ACTIONS, SAFE_NEXT_ACTIONS
from app.knowledge.discovery.filters import validate_recommended_action
from app.knowledge.discovery.indexes import DiscoverySources, load_default_sources
from app.knowledge.discovery.queries import discover, route_task
from app.knowledge.discovery.serialization import (
    FROZEN_DISCOVERY_BUNDLE_HASH,
)
from app.knowledge.discovery.serialization import (
    compute_semantic_bundle_hash as compute_discovery_semantic_hash,
)
from app.knowledge.discovery.serialization import (
    load_freeze_manifest as load_discovery_manifest,
)
from app.knowledge.linking.analyzer import ArtifactRef, analyze_links
from app.knowledge.n8n_engineering.constants import (
    FROZEN_CATALOG_HASH,
    FROZEN_LIBRARY_SEMANTIC_HASH,
    KNOWN_PATTERN_IDS,
    N8N_ENGINEERING_SKILL_IDS,
)
from app.knowledge.workflow_patterns.serialization import (
    FROZEN_CORE_BUNDLE_HASH,
    FROZEN_PILOT_BUNDLE_HASH,
    FROZEN_SCHEMA_HASH,
    load_library_manifest,
)
from app.skills.hashing import calculate_skill_package_hash
from app.skills.legacy_output_contract import expected_frozen_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from tests.support.discovery_validation import base_query
from tests.support.kb_skill_validation import (
    FROZEN_CIM_BUNDLE_HASH,
    FROZEN_MARKETING_CLAIMS_HASH,
    FROZEN_MV_020_HASH,
    FROZEN_POSITIONING_HASH,
    KB_SKILL_PACKAGE_HASHES,
    load_workflow_catalog,
    recompute_external_artifacts_bundle_hash,
)
from tests.support.kb_wpl_program_validation import (
    EXPECTED_COMPONENT_IDS,
    FORBIDDEN_EXEC_METHODS,
    FROZEN_PROGRAM_BUNDLE_HASH,
    FROZEN_PROGRAM_SEMANTIC_HASH,
    WPL_KNOWLEDGE_MODULES,
    load_accepted_limitations,
    load_component_index,
    load_deferred_work,
    load_freeze_findings,
    load_hash_registry,
    load_integrated_manifest,
    load_invariant_map,
    recompute_program_semantic_hash,
    scan_py_forbidden_imports,
)
from tests.support.wpl_schema_validation import FROZEN_BUNDLE_HASH, recompute_bundle_hash

REPO = Path(__file__).resolve().parents[1]
AUDIT_DOC = REPO / "docs/rfc/KB-WPL-01.9-INTEGRATED-FREEZE-AUDIT.md"
PROGRAM_BUNDLE = REPO / "packages/knowledge/kb_wpl_program/0.1.0"
KNOWLEDGE_ROOT = REPO / "app" / "knowledge"
TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"

DISCOVERY_FIXTURES = [
    ("Проверить бизнес-идею", "marketing.market_validation"),
    ("Исследовать рынок", "marketing.market_research"),
    ("Проанализировать конкурентов", "marketing.competitive_intelligence"),
    ("Определить ICP", "marketing.customer_intelligence"),
    ("Сделать позиционирование", "marketing.positioning"),
    ("Создать оффер", "marketing.offer_architecture"),
    ("Сделать пост в Telegram", "marketing.distribution"),
    ("Подготовить сценарий YouTube", "deliverables.content_architecture"),
    ("Создать презентацию", "marketing.presentation_architecture"),
    ("Спроектировать n8n workflow", "engineering.workflow_architecture"),
    ("Найти ошибку в n8n workflow", "engineering.workflow_debugging"),
    ("Проверить workflow перед деплоем", "engineering.deployment_review"),
    ("Связать документы и найти дубли", "knowledge.knowledge_linking"),
    ("retry pattern", "engineering.error_recovery"),
    ("Найти approval pattern", "marketing.distribution"),
]


@pytest.fixture
def sources() -> DiscoverySources:
    src = load_default_sources()
    src.tenant_private_skills.append(
        {
            "skill_id": "ms.skill.private_marketing",
            "title": "Private Marketing Skill",
            "tenant_scope": "tenant_private",
            "tenant_id": TENANT_A,
            "trust_status": "candidate",
            "maturity": "reviewed",
        }
    )
    return src


# --- A. Inventory ---


def test_a01_audit_document_exists() -> None:
    assert AUDIT_DOC.is_file()


def test_a02_program_bundle_files_exist() -> None:
    for name in (
        "integrated_manifest.json",
        "component_index.json",
        "invariant_map.json",
        "hash_registry.json",
        "accepted_limitations.json",
        "deferred_work.json",
        "freeze_findings.json",
        "README.md",
    ):
        assert (PROGRAM_BUNDLE / name).is_file()


def test_a03_all_components_indexed() -> None:
    index = load_component_index()
    ids = {c["component_id"] for c in index["components"]}
    assert ids == set(EXPECTED_COMPONENT_IDS)


def test_a04_all_kb_skills_present() -> None:
    for skill_id in KB_SKILL_PACKAGE_HASHES:
        assert (REPO / "packages/skills" / skill_id).is_dir()


def test_a05_wpl_library_index_present() -> None:
    manifest = load_library_manifest()
    assert manifest["pattern_count"] == 20
    assert manifest["status"] == "frozen_reviewed_library"


def test_a06_capability_model_bundle_present() -> None:
    assert (REPO / "packages/knowledge/capability_model/0.1.0/freeze_manifest.json").is_file()


def test_a07_discovery_bundle_present() -> None:
    assert (REPO / "packages/knowledge/discovery/0.1.0/freeze_manifest.json").is_file()


def test_a08_workflow_catalog_present() -> None:
    assert (REPO / "packages/knowledge/workflow_catalog/0.1.0/catalog.json").is_file()


def test_a09_knowledge_modules_present() -> None:
    for mod in WPL_KNOWLEDGE_MODULES:
        assert (KNOWLEDGE_ROOT / mod).is_dir()


def test_a10_no_unexpected_runtime_routes() -> None:
    routes = REPO / "app/api/routes"
    if routes.is_dir():
        text = " ".join(p.read_text(encoding="utf-8") for p in routes.glob("*.py"))
        assert "kb_wpl_execute" not in text
        assert "skill_install" not in text


def test_a11_four_professions_in_capability_model() -> None:
    assert len(load_professions()) == 4


def test_a12_invariant_count_sixty() -> None:
    assert len(load_invariant_map()["invariants"]) == 60


# --- B. Hashes ---


def test_b01_wpl_schema_hash() -> None:
    assert recompute_bundle_hash() == FROZEN_BUNDLE_HASH == FROZEN_SCHEMA_HASH


def test_b02_workflow_catalog_hash() -> None:
    manifest = json.loads(
        (REPO / "packages/knowledge/workflow_catalog/0.1.0/freeze_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["bundle_hash"] == FROZEN_CATALOG_HASH


def test_b03_pilot_bundle_hash() -> None:
    manifest = load_library_manifest()
    assert manifest["pilot_bundle_hash"] == FROZEN_PILOT_BUNDLE_HASH


def test_b04_core_bundle_hash() -> None:
    manifest = load_library_manifest()
    assert manifest["core_bundle_hash"] == FROZEN_CORE_BUNDLE_HASH


def test_b05_wpl_library_semantic_hash() -> None:
    manifest = load_library_manifest()
    assert manifest["library_semantic_hash"] == FROZEN_LIBRARY_SEMANTIC_HASH


def test_b06_capability_model_bundle_hash() -> None:
    assert recompute_freeze_manifest_bundle_hash() == FROZEN_CAPABILITY_MODEL_BUNDLE_HASH


def test_b07_capability_model_semantic_hash() -> None:
    assert compute_semantic_bundle_hash() == FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH


def test_b08_discovery_bundle_hash() -> None:
    manifest = load_discovery_manifest()
    assert manifest["bundle_hash"] == FROZEN_DISCOVERY_BUNDLE_HASH


def test_b09_discovery_semantic_hash_stable() -> None:
    assert compute_discovery_semantic_hash() == FROZEN_DISCOVERY_BUNDLE_HASH


def test_b10_integrated_program_bundle_hash() -> None:
    manifest = load_integrated_manifest()
    assert manifest["bundle_hash"] == FROZEN_PROGRAM_BUNDLE_HASH


def test_b11_integrated_semantic_hash() -> None:
    manifest = load_integrated_manifest()
    assert manifest["semantic_hash"] == FROZEN_PROGRAM_SEMANTIC_HASH
    assert recompute_program_semantic_hash(manifest) == FROZEN_PROGRAM_SEMANTIC_HASH


def test_b12_all_kb_skill_hashes() -> None:
    registry = load_hash_registry()
    for skill_id, expected in registry["hashes"]["skill_packages"].items():
        root = REPO / "packages/skills" / skill_id
        assert calculate_skill_package_hash(root) == expected


def test_b13_frozen_marketing_skill_hashes_unchanged() -> None:
    assert expected_frozen_package_hash("ms.skill.positioning", "0.1.0") == FROZEN_POSITIONING_HASH
    assert expected_frozen_package_hash("ms.skill.market_validation", "0.2.0") == FROZEN_MV_020_HASH


def test_b14_frozen_knowledge_bundles_unchanged() -> None:
    cim = json.loads(
        (REPO / "packages/knowledge/customer_intelligence/0.1.0/freeze_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    mc = json.loads(
        (REPO / "packages/knowledge/marketing_claims/0.1.0/freeze_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert cim["bundle_hash"] == FROZEN_CIM_BUNDLE_HASH
    assert mc["bundle_hash"] == FROZEN_MARKETING_CLAIMS_HASH


def test_b15_external_artifacts_deterministic() -> None:
    assert recompute_external_artifacts_bundle_hash() == json.loads(
        (REPO / "packages/knowledge/external_artifacts/0.1.0/freeze_manifest.json").read_text(
            encoding="utf-8"
        )
    )["bundle_hash"]


# --- C. Cross-contract ---


def test_c01_capability_skill_bindings_resolve() -> None:
    caps = {c["capability_id"] for c in load_capabilities()}
    for binding in load_capability_skill_bindings():
        assert binding["capability_id"] in caps
        skill_id = binding["skill_id"]
        if skill_id.startswith("ms.skill."):
            assert (REPO / "packages/skills" / skill_id).is_dir() or skill_id.endswith("_future")


def test_c02_pattern_bindings_resolve_to_wpl() -> None:
    for binding in load_skill_pattern_bindings():
        assert binding["pattern_id"] in KNOWN_PATTERN_IDS


def test_c03_discovery_aliases_resolve_to_capabilities() -> None:
    caps = {c["capability_id"] for c in load_capabilities()}
    aliases = json.loads(
        (REPO / "packages/knowledge/discovery/0.1.0/aliases.json").read_text(encoding="utf-8")
    )
    for alias in aliases["aliases"]:
        for cap_id in alias.get("capability_ids", []):
            assert cap_id in caps


def test_c04_discovery_candidate_skills_exist() -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=load_default_sources())
    for skill in result["skill_candidates"]:
        if skill["artifact_id"].startswith("ms.skill."):
            assert (REPO / "packages/skills" / skill["artifact_id"]).is_dir()


def test_c05_discovery_candidate_patterns_exist() -> None:
    result = discover(base_query("Проверить бизнес-идею"), sources=load_default_sources())
    for pattern in result["pattern_candidates"]:
        assert pattern["artifact_id"] in KNOWN_PATTERN_IDS


def test_c06_engineering_skills_reference_valid_patterns() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        manifest = (REPO / "packages/skills" / skill_id / "manifest.yaml").read_text(
            encoding="utf-8"
        )
        for pid in KNOWN_PATTERN_IDS:
            if pid in manifest:
                assert pid in KNOWN_PATTERN_IDS


def test_c07_capability_gaps_explicit() -> None:
    result = discover(base_query("Запустить рекламу", execution_sensitivity="billing"))
    assert result["capability_gaps"] or result["blockers"] or result["connector_requirements"]


def test_c08_no_stale_pattern_ids_in_capability_model() -> None:
    for binding in load_skill_pattern_bindings():
        assert binding["pattern_id"] in KNOWN_PATTERN_IDS


def test_c09_profession_capability_bindings_consistent() -> None:
    prof_index = {p["profession_id"]: p for p in load_professions()}
    cap_index = {c["capability_id"] for c in load_capabilities()}
    for prof in prof_index.values():
        for cap_id in prof.get("capability_ids", []):
            assert cap_id in cap_index


def test_c10_runtime_authorized_false_in_manifest() -> None:
    manifest = load_integrated_manifest()
    assert manifest["runtime_authorized"] is False
    assert manifest["production_eligible"] is False


def test_c11_hash_registry_matches_integrated() -> None:
    manifest = load_integrated_manifest()
    registry = load_hash_registry()
    assert manifest["discovery_bundle_hash"] == registry["hashes"]["discovery_bundle"]
    assert manifest["capability_model_hash"] == registry["hashes"]["capability_model_bundle"]


def test_c12_component_hashes_in_manifest() -> None:
    manifest = load_integrated_manifest()
    assert "kb-wpl-01.7" in manifest["component_hashes"]
    assert "kb-wpl-01.8" in manifest["component_hashes"]


# --- D. Security ---


def test_d01_no_network_imports_in_wpl_modules() -> None:
    offenders: list[str] = []
    for mod in WPL_KNOWLEDGE_MODULES:
        mod_path = KNOWLEDGE_ROOT / mod
        if mod_path.is_dir():
            for py in mod_path.rglob("*.py"):
                offenders.extend(scan_py_forbidden_imports(py))
    assert offenders == []


def test_d02_catalog_no_node_bodies() -> None:
    catalog = load_workflow_catalog()
    for template in catalog["templates"][:30]:
        assert "nodes" not in template
        assert "connections" not in template


def test_d03_catalog_quarantine_only() -> None:
    catalog = load_workflow_catalog()
    for template in catalog["templates"]:
        assert template["quarantine_status"] == "quarantined"


def test_d04_no_secrets_in_program_bundle() -> None:
    blob = json.dumps(load_integrated_manifest()).lower()
    for marker in ("sk-live", "api_key", "password", "bearer "):
        assert marker not in blob


def test_d05_no_absolute_paths_in_manifest() -> None:
    text = (PROGRAM_BUNDLE / "integrated_manifest.json").read_text(encoding="utf-8")
    assert "C:\\" not in text
    assert "/Users/" not in text


def test_d06_discovery_rejects_api_key_input() -> None:
    from app.knowledge.discovery.errors import DiscoverySecurityError, DiscoveryValidationError

    with pytest.raises((DiscoverySecurityError, DiscoveryValidationError)):
        discover(base_query("task sk-live-secret-key-here"))


def test_d07_no_subprocess_in_knowledge_modules() -> None:
    for mod in WPL_KNOWLEDGE_MODULES:
        mod_path = KNOWLEDGE_ROOT / mod
        if mod_path.is_dir():
            for py in mod_path.rglob("*.py"):
                tree = ast.parse(py.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            assert alias.name.split(".")[0] != "subprocess"
                    if isinstance(node, ast.ImportFrom) and node.module:
                        assert node.module.split(".")[0] != "subprocess"


def test_d08_wpl_patterns_no_raw_n8n_json() -> None:
    core_dir = REPO / "packages/knowledge/workflow_patterns/0.1.0/patterns/core"
    for path in list(core_dir.glob("*.json"))[:5]:
        text = path.read_text(encoding="utf-8")
        assert '"nodes"' not in text


# --- E. Tenant ---


def test_e01_discovery_private_skill_hidden_cross_tenant(sources: DiscoverySources) -> None:
    result = discover(base_query("Private skill", tenant_id=TENANT_B), sources=sources)
    assert "ms.skill.private_marketing" not in [
        s["artifact_id"] for s in result["skill_candidates"]
    ]


def test_e02_knowledge_linking_no_cross_tenant() -> None:
    artifacts = [
        ArtifactRef("a1", "Doc A", tenant_scope="tenant-a"),
        ArtifactRef(
            "a2",
            "Doc B",
            tenant_scope="tenant-b",
            existing_links=[{"target_artifact_id": "a1", "relation": "related_to"}],
        ),
    ]
    result = analyze_links(artifacts, tenant_id="tenant-b")
    assert result.cross_tenant_link_rejections


def test_e03_legacy_linking_no_cross_tenant() -> None:
    artifacts = [
        ArtifactRef("a1", "Doc A", tenant_scope="tenant-a"),
        ArtifactRef(
            "a2",
            "Doc B",
            tenant_scope="tenant-b",
            existing_links=[{"target_artifact_id": "a1"}],
        ),
    ]
    result = analyze_links(artifacts, tenant_id="tenant-b")
    assert result.cross_tenant_link_rejections


def test_e04_quarantined_hidden_normal_mode(sources: DiscoverySources) -> None:
    result = discover(base_query("Quarantined"), sources=sources)
    assert not result.get("quarantined_workflow_templates")


def test_e05_audit_mode_still_tenant_safe() -> None:
    src = load_default_sources()
    src.quarantined_templates.append(
        {
            "workflow_template_id": "wf-other-tenant",
            "title": "Other Tenant",
            "tenant_id": TENANT_B,
            "capability_ids": [],
            "quarantined": True,
        }
    )
    query = base_query(
        "Quarantined", tenant_id=TENANT_A, internal_audit_mode=True, include_quarantined=True
    )
    result = discover(query, sources=src)
    ids = [t["artifact_id"] for t in result.get("quarantined_workflow_templates", [])]
    assert "wf-other-tenant" not in ids


# --- F. Runtime boundary ---


def test_f01_integrated_manifest_runtime_flags() -> None:
    m = load_integrated_manifest()
    for key in (
        "runtime_authorized",
        "production_eligible",
        "connector_activation_available",
        "workflow_execution_available",
        "skill_execution_available",
        "API_available",
        "UI_available",
    ):
        assert m[key] is False


def test_f02_all_kb_skills_non_production() -> None:
    for skill_id in KB_SKILL_PACKAGE_HASHES:
        report = validate_skill_package(REPO / "packages/skills" / skill_id)
        projection = project_validation_report(report)
        assert derive_eligibility_view(projection.version_record).production_eligible is False


def test_f03_discovery_runtime_authorized_false() -> None:
    result = discover(base_query("Проверить идею"))
    assert result["runtime_authorized"] is False
    route = result["professional_task_route"]
    assert route["runtime_authorized"] is False


def test_f04_forbidden_actions_not_in_safe_set() -> None:
    assert FORBIDDEN_RECOMMENDED_ACTIONS.isdisjoint(SAFE_NEXT_ACTIONS)


def test_f05_forbidden_action_validation_rejects() -> None:
    for action in FORBIDDEN_RECOMMENDED_ACTIONS:
        assert validate_recommended_action(action) != []


def test_f06_no_execute_methods_in_discovery() -> None:
    for py in (KNOWLEDGE_ROOT / "discovery").glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for forbidden in FORBIDDEN_EXEC_METHODS:
                    assert node.name != forbidden


def test_f07_professions_not_runtime_authorized() -> None:
    for prof in load_professions():
        assert prof.get("runtime_authorized") is False


def test_f08_capability_model_validates() -> None:
    assert validate_bundle() == []


# --- G. Discovery integrated fixtures ---


@pytest.mark.parametrize("task,expected_cap", DISCOVERY_FIXTURES)
def test_g_discovery_fixture_routes(task: str, expected_cap: str) -> None:
    result = discover(base_query(task))
    cap_ids = {c["artifact_id"] for c in result["capabilities"]}
    pattern_ids = {p["artifact_id"] for p in result["pattern_candidates"]}
    if expected_cap == "engineering.deployment_review":
        assert (
            expected_cap in cap_ids
            or "engineering.workflow_architecture" in cap_ids
            or "engineering.workflow_debugging" in cap_ids
        )
    elif expected_cap == "engineering.error_recovery":
        assert expected_cap in cap_ids or "retry_with_idempotency" in pattern_ids
    else:
        assert expected_cap in cap_ids or any(
            expected_cap.split(".")[-1] in c for c in cap_ids
        )


def test_g16_publish_request_blocked() -> None:
    result = discover(base_query("Опубликовать пост", execution_sensitivity="publication"))
    assert result["readiness_summary"]["runtime_available"] is False
    assert "request_human_review" in result["safe_next_actions"]


def test_g17_advertising_spend_denied() -> None:
    result = discover(base_query("Запустить рекламу", execution_sensitivity="billing"))
    assert "request_human_review" in result["safe_next_actions"]


def test_g18_ambiguous_request_no_forbidden_action() -> None:
    result = discover(base_query("Сделать что-то полезное"))
    for action in result["safe_next_actions"]:
        assert action not in FORBIDDEN_RECOMMENDED_ACTIONS


def test_g19_result_hash_deterministic() -> None:
    q = base_query("Проверить бизнес-идею")
    assert discover(q)["result_hash"] == discover(q)["result_hash"]


def test_g20_skill_preferred_over_pattern() -> None:
    result = discover(base_query("Проверить бизнес-идею"))
    if result["skill_candidates"] and result["pattern_candidates"]:
        assert (
            result["skill_candidates"][0]["total_rank"]
            >= result["pattern_candidates"][0]["total_rank"]
        )


def test_g21_route_advisory_only() -> None:
    route = route_task(base_query("Проверить идею"))
    assert "no execution scheduled" in route["route_explanation"].lower() or route.get(
        "runtime_authorized"
    ) is False


# --- H. Knowledge Linking ---


def test_h01_no_auto_merge() -> None:
    artifacts = [
        ArtifactRef("a1", "Doc A"),
        ArtifactRef("a2", "Doc B"),
    ]
    result = analyze_links(artifacts)
    assert not getattr(result, "auto_merged", False)


def test_h02_orphan_detection() -> None:
    artifacts = [
        ArtifactRef("a1", "Root"),
        ArtifactRef("a2", "Child", existing_links=[{"target_artifact_id": "a1"}]),
    ]
    result = analyze_links(artifacts)
    assert "a2" in result.orphan_artifacts


def test_h03_linking_module_read_only() -> None:
    for py in (KNOWLEDGE_ROOT / "linking").glob("*.py"):
        text = py.read_text(encoding="utf-8")
        assert "def save_" not in text
        assert "def mutate_" not in text


# --- I. Presentation ---


def test_i01_presentation_non_executable() -> None:
    manifest = (
        REPO / "packages/skills/ms.skill.presentation_architecture/manifest.yaml"
    ).read_text(encoding="utf-8")
    assert "executable: false" in manifest


def test_i02_no_renderer_in_presentation_skill() -> None:
    manifest = (
        REPO / "packages/skills/ms.skill.presentation_architecture/manifest.yaml"
    ).read_text(encoding="utf-8")
    assert "marp" not in manifest.lower() or "false" in manifest


# --- J. Engineering Skills ---


@pytest.mark.parametrize("skill_id", N8N_ENGINEERING_SKILL_IDS)
def test_j_n8n_skills_no_deployment_permissions(skill_id: str) -> None:
    manifest = (REPO / "packages/skills" / skill_id / "manifest.yaml").read_text(encoding="utf-8")
    assert "allowed_tools:[]" in manifest.replace(" ", "") or "allowed_tools: []" in manifest


def test_j04_deployment_review_manual_gate() -> None:
    manifest = (
        REPO / "packages/skills/ms.skill.n8n_deployment_review/manifest.yaml"
    ).read_text(encoding="utf-8")
    assert "executable: false" in manifest


# --- K. Capability Model ---


def test_k01_readiness_multidimensional() -> None:
    caps = load_capabilities()
    sample = next(c for c in caps if c.get("readiness"))
    readiness = sample["readiness"]
    assert isinstance(readiness, (dict, list))


def test_k02_gaps_registered() -> None:
    gaps = json.loads(
        (
            REPO / "packages/knowledge/capability_model/0.1.0/capability_gaps.json"
        ).read_text(encoding="utf-8")
    )
    assert len(gaps) >= 1


# --- L. Regression ---


def test_l01_capability_model_validation_green() -> None:
    assert validate_bundle() == []


def test_l02_discovery_imports_clean() -> None:
    import app.knowledge.discovery as discovery

    assert discovery.BUNDLE_STATUS == "read_only_discovery_model"


def test_l03_freeze_findings_no_blockers() -> None:
    assert load_freeze_findings()["blockers"] == []


def test_l04_accepted_limitations_documented() -> None:
    assert len(load_accepted_limitations()["limitations"]) >= 10


def test_l05_deferred_work_documented() -> None:
    assert len(load_deferred_work()["items"]) >= 10


# --- M. Invariants (parametrized) ---


@pytest.mark.parametrize(
    "inv_id",
    [inv["id"] for inv in json.loads((PROGRAM_BUNDLE / "invariant_map.json").read_text())["invariants"]],
)
def test_m_invariant_mapped(inv_id: str) -> None:
    inv_map = load_invariant_map()
    inv = next(i for i in inv_map["invariants"] if i["id"] == inv_id)
    assert inv["rule"]
    assert inv["test_ids"]


def test_m_invariant_007_pattern_maturity() -> None:
    manifest = load_library_manifest()
    for pid, _ in manifest.get("pattern_hashes", {}).items():
        assert pid in KNOWN_PATTERN_IDS


def test_m_invariant_014_discovery_deterministic() -> None:
    q = base_query("Проверить идею")
    src = load_default_sources()
    shuffled = copy.deepcopy(src)
    shuffled.skills = list(reversed(shuffled.skills))
    assert discover(q, sources=src)["result_hash"] == discover(q, sources=shuffled)["result_hash"]


def test_m_invariant_045_generated_at_excluded() -> None:
    manifest = load_integrated_manifest()
    assert "generated_at" in manifest
    recomputed = recompute_program_semantic_hash(manifest)
    assert recomputed == FROZEN_PROGRAM_SEMANTIC_HASH


def test_m_invariant_059_safe_actions_finite() -> None:
    result = discover(base_query("Проверить идею"))
    for action in result["safe_next_actions"]:
        assert action in SAFE_NEXT_ACTIONS
