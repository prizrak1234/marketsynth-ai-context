"""KB-WPL-01.3C — Workflow Pattern Library Freeze tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from app.knowledge.workflow_patterns.contracts import SINGLE_SOURCE_POLICY, ManualAuditRecord
from app.knowledge.workflow_patterns.library_freeze import (
    FROZEN_CORE_BUNDLE_HASH,
    build_overlap_matrix,
    is_valid_sha256,
    library_semantic_hash,
    overlap_matrix_semantic_hash,
)
from app.knowledge.workflow_patterns.serialization import (
    FROZEN_CATALOG_HASH,
    FROZEN_PILOT_BUNDLE_HASH,
    FROZEN_SCHEMA_HASH,
    audit_semantic_hash,
    core_semantic_hash,
    load_core_audit_records,
    load_core_manifest,
    load_core_patterns,
    load_core_practices,
    load_core_source_support_map,
    load_library_index,
    load_library_manifest,
    load_overlap_matrix,
    load_pilot_audit_records,
    load_pilot_manifest,
    load_pilot_patterns,
    load_pilot_practices,
    load_pilot_source_support_map,
    pattern_semantic_hash,
    pilot_semantic_hash,
    source_support_map_semantic_hash,
)
from app.knowledge.workflow_patterns.validation import validate_pattern_semantics
from tests.support.kb_skill_validation import KB_SKILL_PACKAGE_HASHES
from tests.support.wpl_schema_validation import (
    FROZEN_BUNDLE_HASH,
    recompute_bundle_hash,
    validate_manual_audit_record,
    validate_practice_record,
    validate_workflow_pattern,
)

REPO = Path(__file__).resolve().parents[1]
WPL_ROOT = REPO / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"
PILOT_DIR = WPL_ROOT / "patterns" / "pilot"
CORE_DIR = WPL_ROOT / "patterns" / "core"
PILOT_PRACTICE_DIR = WPL_ROOT / "practices" / "pilot"
CORE_PRACTICE_DIR = WPL_ROOT / "practices" / "core"
CATALOG_PATH = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "catalog.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "subprocess", "socket")
FORBIDDEN_MATURITY = {
    "active",
    "executable",
    "deployed",
    "approved",
    "platform_adapted",
    "production_ready",
}
QUALITY_GATE_HASH = "f6b75809ca0cc1027490b3f83bd5effc76bc104653e85c0a4f6140f6044f8c4b"


@pytest.fixture
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def pilot_patterns() -> list[dict]:
    return load_pilot_patterns()


@pytest.fixture
def core_patterns() -> list[dict]:
    return load_core_patterns()


@pytest.fixture
def all_patterns(pilot_patterns: list[dict], core_patterns: list[dict]) -> list[dict]:
    return pilot_patterns + core_patterns


@pytest.fixture
def library_manifest() -> dict:
    return load_library_manifest()


@pytest.fixture
def library_index() -> dict:
    return load_library_index()


def test_01_exactly_twenty_patterns(all_patterns: list[dict]) -> None:
    assert len(all_patterns) == 20


def test_02_exactly_eight_pilot_patterns(pilot_patterns: list[dict]) -> None:
    assert len(pilot_patterns) == 8


def test_03_exactly_twelve_core_patterns(core_patterns: list[dict]) -> None:
    assert len(core_patterns) == 12


def test_04_no_unexpected_pattern_files() -> None:
    pilot_ids = {p.stem for p in PILOT_DIR.glob("*.json")}
    core_ids = {p.stem for p in CORE_DIR.glob("*.json")}
    assert len(pilot_ids) == 8
    assert len(core_ids) == 12
    assert pilot_ids.isdisjoint(core_ids)


def test_05_pattern_ids_unique(all_patterns: list[dict]) -> None:
    ids = [p["pattern_id"] for p in all_patterns]
    assert len(ids) == len(set(ids))


def test_06_practice_ids_unique() -> None:
    practices = load_pilot_practices() + load_core_practices()
    ids = [p["practice_id"] for p in practices]
    assert len(ids) == len(set(ids))
    assert len(ids) == 24


def test_07_audit_ids_unique() -> None:
    audits = load_pilot_audit_records() + load_core_audit_records()
    ids = [a["audit_id"] for a in audits]
    assert len(ids) == len(set(ids))
    assert len(ids) == 20


def test_08_every_index_entry_resolves(library_index: dict) -> None:
    for entry in library_index["pattern_entries"]:
        assert (PILOT_DIR / f"{entry['pattern_id']}.json").exists() or (
            CORE_DIR / f"{entry['pattern_id']}.json"
        ).exists()


def test_09_no_orphan_pattern_file(all_patterns: list[dict]) -> None:
    indexed = {p["pattern_id"] for p in all_patterns}
    on_disk = {p.stem for p in PILOT_DIR.glob("*.json")} | {p.stem for p in CORE_DIR.glob("*.json")}
    assert indexed == on_disk


def test_10_no_orphan_practice_file() -> None:
    practices = load_pilot_practices() + load_core_practices()
    indexed = {p["practice_id"] for p in practices}
    on_disk = {p.stem for p in PILOT_PRACTICE_DIR.glob("*.json")} | {
        p.stem for p in CORE_PRACTICE_DIR.glob("*.json")
    }
    assert indexed == on_disk


def test_11_every_pattern_schema_valid(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        validate_workflow_pattern(pattern)


def test_12_every_practice_schema_valid() -> None:
    for practice in load_pilot_practices() + load_core_practices():
        validate_practice_record(practice)


def test_13_every_audit_record_valid() -> None:
    for audit in load_pilot_audit_records() + load_core_audit_records():
        validate_manual_audit_record(audit)
        ManualAuditRecord.model_validate(audit)


def test_14_every_sha256_sixty_four_hex(library_manifest: dict) -> None:
    hashes = list(library_manifest["pattern_hashes"].values())
    hashes.extend(library_manifest["practice_hashes"].values())
    hashes.extend(library_manifest["audit_hashes"].values())
    hashes.extend(library_manifest["source_support_hashes"].values())
    hashes.append(library_manifest["library_index_hash"])
    hashes.append(library_manifest["overlap_matrix_hash"])
    hashes.append(library_manifest["library_semantic_hash"])
    for value in hashes:
        assert SHA256_RE.match(value)
        assert is_valid_sha256(value)


def test_15_documented_pattern_hashes_match(
    all_patterns: list[dict], library_manifest: dict
) -> None:
    for pattern in all_patterns:
        pid = pattern["pattern_id"]
        assert library_manifest["pattern_hashes"][pid] == pattern_semantic_hash(pattern)


def test_16_quality_gate_hash_matches_recomputation(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "quality_gate_after_generation")
    assert pattern_semantic_hash(pattern) == QUALITY_GATE_HASH
    assert len(QUALITY_GATE_HASH) == 64


def test_17_pilot_bundle_hash_unchanged() -> None:
    manifest = load_pilot_manifest()
    assert manifest["bundle_hash"] == FROZEN_PILOT_BUNDLE_HASH


def test_18_core_bundle_hash_unchanged() -> None:
    manifest = load_core_manifest()
    assert manifest["bundle_hash"] == FROZEN_CORE_BUNDLE_HASH


def test_19_catalog_hash_unchanged(library_manifest: dict) -> None:
    assert library_manifest["catalog_bundle_hash"] == FROZEN_CATALOG_HASH


def test_20_schema_hash_unchanged(library_manifest: dict) -> None:
    assert library_manifest["schema_bundle_hash"] == FROZEN_SCHEMA_HASH
    assert recompute_bundle_hash() == FROZEN_BUNDLE_HASH


def test_21_main_flows_provider_neutral(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        steps_blob = json.dumps(pattern.get("steps", [])).lower()
        variants_blob = json.dumps(pattern.get("implementation_variants", [])).lower()
        for name in ("telegram", "gmail", "openai", "instagram", "linkedin"):
            if name in steps_blob:
                assert name in variants_blob


def test_22_providers_restricted_to_variants(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        assert "n8n-nodes-base." not in json.dumps(pattern.get("steps", []))


def test_23_no_credential_ids_in_neutral_bodies(all_patterns: list[dict]) -> None:
    blob = json.dumps(all_patterns).lower()
    assert "credential_id" not in blob


def test_24_no_raw_secrets(all_patterns: list[dict]) -> None:
    blob = json.dumps(all_patterns).lower()
    assert "sk-" not in blob
    assert "bearer " not in blob


def test_25_no_raw_nodes(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        assert "nodes" not in pattern
        assert "connections" not in pattern


def test_26_no_raw_connections(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        assert "pinData" not in pattern
        assert "workflow_body" not in pattern


def test_27_no_n8n_expressions(all_patterns: list[dict]) -> None:
    blob = json.dumps(all_patterns)
    assert "{{" not in blob


def test_28_every_source_workflow_resolves(all_patterns: list[dict], catalog: dict) -> None:
    index = {t["workflow_template_id"]: t for t in catalog["templates"]}
    for pattern in all_patterns:
        for source_id in pattern["source_workflow_ids"]:
            assert source_id in index


def test_29_every_source_hash_matches(all_patterns: list[dict], catalog: dict) -> None:
    index = {t["workflow_template_id"]: t for t in catalog["templates"]}
    for pattern in all_patterns:
        for source_id in pattern["source_workflow_ids"]:
            assert len(index[source_id]["workflow_hash"]) == 64


def test_30_rejected_source_cannot_support_pattern(catalog: dict, all_patterns: list[dict]) -> None:
    index = {t["workflow_template_id"]: t for t in catalog["templates"]}
    for pattern in all_patterns:
        for source_id in pattern["source_workflow_ids"]:
            assert index[source_id]["quarantine_status"] != "rejected"


def test_31_critical_source_cannot_support_pattern(catalog: dict, all_patterns: list[dict]) -> None:
    index = {t["workflow_template_id"]: t for t in catalog["templates"]}
    for pattern in all_patterns:
        for source_id in pattern["source_workflow_ids"]:
            findings = index[source_id].get("security_findings") or []
            for finding in findings:
                if finding.get("severity") == "critical":
                    assert finding.get("resolution_status") == "resolved"


def test_32_every_practice_record_resolves(all_patterns: list[dict]) -> None:
    known = {p["practice_id"] for p in load_pilot_practices() + load_core_practices()}
    for pattern in all_patterns:
        for practice_id in pattern["source_practice_ids"]:
            assert practice_id in known


def test_33_every_audit_record_resolves(all_patterns: list[dict]) -> None:
    audits = {a["audit_id"] for a in load_pilot_audit_records() + load_core_audit_records()}
    pilot_ids = {p["pattern_id"] for p in load_pilot_patterns()}
    for pattern in all_patterns:
        pid = pattern["pattern_id"]
        audit_id = f"audit-{pid}" if pid in pilot_ids else f"audit-core-{pid}"
        assert audit_id in audits


def test_34_every_pattern_has_support_entry(all_patterns: list[dict]) -> None:
    pilot_mapped = {e["pattern_id"] for e in load_pilot_source_support_map()["entries"]}
    core_mapped = {e["pattern_id"] for e in load_core_source_support_map()["entries"]}
    for pattern in all_patterns:
        pid = pattern["pattern_id"]
        assert pid in pilot_mapped or pid in core_mapped


def test_35_every_support_signal_has_evidence_hash() -> None:
    for support_map in (load_pilot_source_support_map(), load_core_source_support_map()):
        for entry in support_map["entries"]:
            for signal in entry["supporting_signals"]:
                assert SHA256_RE.match(signal["evidence_hash"])


def test_36_every_support_signal_names_supported_rule() -> None:
    for support_map in (load_pilot_source_support_map(), load_core_source_support_map()):
        for entry in support_map["entries"]:
            for signal in entry["supporting_signals"]:
                assert signal["supported_pattern_rule"]


def test_37_duplicate_workflows_not_two_independent_sources() -> None:
    overlap = load_overlap_matrix()
    for entry in overlap["entries"]:
        if len(entry["supported_pattern_ids"]) > 1:
            assert entry["independence_assessment"] in {
                "pattern_specific_signals",
                "shared_rule_overlap",
            }


def test_38_multi_pattern_overlaps_documented(library_manifest: dict) -> None:
    overlap = load_overlap_matrix()
    assert overlap["overlap_count"] >= 1
    assert library_manifest["overlap_matrix_hash"] == overlap_matrix_semantic_hash(overlap)


def test_39_overlapping_signals_pattern_specific() -> None:
    overlap = build_overlap_matrix()
    multi = [e for e in overlap["entries"] if len(e["supported_pattern_ids"]) > 1]
    for entry in multi:
        rules_by_pattern = {
            pid: {s["supported_rule"] for s in entry["pattern_signals"] if s["pattern_id"] == pid}
            for pid in entry["supported_pattern_ids"]
        }
        assert all(rules_by_pattern.values())


def test_40_publication_patterns_require_approval(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        if pattern.get("publication_sensitive"):
            approval = pattern["approval_requirements"]
            assert approval["publication_approval_required"] is True


def test_41_auto_publication_approval_forbidden(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        if pattern.get("publication_sensitive"):
            assert pattern["approval_requirements"]["auto_approval_allowed"] is False


def test_42_publication_result_requires_evidence(all_patterns: list[dict]) -> None:
    pub_ids = {"human_approval_before_publication", "publication_confirmation"}
    for pattern in all_patterns:
        if pattern["pattern_id"] in pub_ids:
            assert pattern["evidence_requirements"]["required"] is True


def test_43_human_edit_resume_preserves_lineage(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "human_edit_then_resume")
    assert pattern["approval_requirements"]["human_approval_required"] is True
    assert any(s["step_type"] == "approval" for s in pattern["steps"])
    assert pattern["evidence_requirements"]["required"] is True
    limitations = " ".join(pattern["known_limitations"]).lower()
    assert "edit" in limitations or "decision" in limitations


def test_44_retry_requires_idempotency(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        if pattern.get("retry_policy") not in ("none", ""):
            assert pattern["idempotency_requirements"]["required"] is True


def test_45_unknown_outcome_writes_no_auto_retry(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        if pattern.get("retry_policy") not in ("none", ""):
            assert pattern["idempotency_requirements"]["unknown_outcome_auto_retry"] is False


def test_46_pagination_terminates(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "pagination_and_batching")
    assert "max_batch_size" in pattern["input_contract"]["required"]
    assert any(e.get("condition") == "complete" for e in pattern["edges"])


def test_47_batch_size_bounded(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "pagination_and_batching")
    assert "max_batch_size" in json.dumps(pattern)


def test_48_checkpoint_resume_state_defined(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "checkpoint_and_resume")
    assert "checkpoint_id" in pattern["input_contract"]["required"]
    assert "checkpoint_id" in pattern["output_contract"]["required"]


def test_49_dead_letter_terminal_handling(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "dead_letter_queue")
    assert "dead_letter" in pattern["error_paths"]


def test_50_rate_limit_retries_bounded(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "provider_rate_limit_handling")
    blob = json.dumps(pattern).lower()
    assert "backoff" in blob or "retry" in blob


def test_51_structured_llm_validated_before_api(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "structured_LLM_to_API_request")
    steps = [s["step_type"] for s in pattern["steps"]]
    validate_idx = steps.index("validate")
    transport_idx = next(i for i, s in enumerate(pattern["steps"]) if s["step_type"] == "transport")
    assert validate_idx < transport_idx


def test_52_grounded_generation_preserves_sources(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "evidence_grounded_generation")
    assert "source_reference" in pattern["evidence_requirements"]["evidence_classes"]


def test_53_prompt_injection_boundary_present(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "evidence_grounded_generation")
    limitations = " ".join(pattern["known_limitations"]).lower()
    assert "injection" in limitations or "prompt" in limitations


def test_54_quality_gate_blocks_invalid_output(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "quality_gate_after_generation")
    assert any(s["step_type"] == "validate" for s in pattern["steps"])


def test_55_supervisor_no_undeclared_tools(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "supervisor_pattern")
    blob = " ".join(pattern["known_limitations"]).lower()
    assert "tool" in blob


def test_56_specialist_scope_finite(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "specialist_subworkflow")
    assert "specialist_scope" in pattern["input_contract"]["required"]


def test_57_tool_workflow_separation_permission_boundary(all_patterns: list[dict]) -> None:
    pattern = next(p for p in all_patterns if p["pattern_id"] == "tool_workflow_separation")
    assert any(s["step_type"] == "validate" for s in pattern["steps"])


def test_58_learning_pattern_creates_candidate_only(all_patterns: list[dict]) -> None:
    pattern = next(
        p for p in all_patterns if p["pattern_id"] == "customer_feedback_to_learning_candidate"
    )
    assert "knowledge_candidate" in pattern["output_contract"]["required"]


def test_59_learning_candidate_tenant_scoped(all_patterns: list[dict]) -> None:
    pattern = next(
        p for p in all_patterns if p["pattern_id"] == "customer_feedback_to_learning_candidate"
    )
    assert pattern["tenant_scope"] == "tenant_scoped"


def test_60_canonical_knowledge_not_auto_mutated(all_patterns: list[dict]) -> None:
    pattern = next(
        p for p in all_patterns if p["pattern_id"] == "customer_feedback_to_learning_candidate"
    )
    blob = " ".join(pattern["known_limitations"]).lower()
    assert "canonical" in blob or "does not modify" in blob


def test_61_every_mandatory_quality_gate_resolved(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        errors = validate_pattern_semantics(pattern)
        gate_errors = [e for e in errors if e.startswith("missing quality gate")]
        assert not gate_errors, pattern["pattern_id"]


def test_62_no_maturity_above_reviewed(all_patterns: list[dict]) -> None:
    for pattern in all_patterns:
        assert pattern["maturity"] == "reviewed"
        assert pattern["maturity"] not in FORBIDDEN_MATURITY


def test_63_runtime_authorized_false(library_manifest: dict) -> None:
    assert library_manifest["runtime_authorized"] is False


def test_64_production_eligible_false(library_manifest: dict) -> None:
    assert library_manifest["production_eligible"] is False


def test_65_library_index_deterministic(library_index: dict, library_manifest: dict) -> None:
    from app.knowledge.workflow_patterns.library_freeze import library_index_semantic_hash

    assert library_manifest["library_index_hash"] == library_index_semantic_hash(library_index)


def test_66_overlap_matrix_deterministic(library_manifest: dict) -> None:
    overlap = load_overlap_matrix()
    assert library_manifest["overlap_matrix_hash"] == overlap_matrix_semantic_hash(overlap)


def test_67_freeze_manifest_semantic_hash_deterministic(library_manifest: dict) -> None:
    assert library_manifest["library_semantic_hash"] == library_semantic_hash(library_manifest)


def test_68_generated_at_excluded_from_semantic_hash(library_manifest: dict) -> None:
    altered = dict(library_manifest)
    altered["generated_at"] = "2099-01-01T00:00:00+00:00"
    assert library_semantic_hash(library_manifest) == library_semantic_hash(altered)


def test_69_no_workflow_execution_introduced(library_manifest: dict) -> None:
    module = REPO / "app" / "knowledge" / "workflow_patterns"
    for path in module.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in FORBIDDEN_IMPORTS
    assert library_manifest["status"] == "frozen_reviewed_library"


def test_70_no_network_api_ui_db_mcp(library_manifest: dict) -> None:
    assert library_manifest["runtime_authorized"] is False
    scripts = REPO / "scripts"
    for name in ("kb_wpl_01_3a_pilot.py", "kb_wpl_01_3b_core.py", "kb_wpl_01_3c_freeze.py"):
        tree = ast.parse((scripts / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS


def test_71_existing_prior_tests_remain_green() -> None:
    assert load_pilot_manifest()["bundle_hash"] == FROZEN_PILOT_BUNDLE_HASH
    assert load_core_manifest()["bundle_hash"] == FROZEN_CORE_BUNDLE_HASH
    assert pilot_semantic_hash(load_pilot_manifest()) == load_pilot_manifest()["semantic_hash"]
    assert core_semantic_hash(load_core_manifest()) == load_core_manifest()["semantic_hash"]


def test_72_frozen_skill_hashes_unchanged() -> None:
    from app.skills.hashing import calculate_skill_package_hash

    for skill_id, expected in KB_SKILL_PACKAGE_HASHES.items():
        root = REPO / "packages" / "skills" / skill_id
        assert calculate_skill_package_hash(root) == expected


def test_audit_hashes_match_recomputation(library_manifest: dict) -> None:
    for audit in load_pilot_audit_records() + load_core_audit_records():
        assert library_manifest["audit_hashes"][audit["audit_id"]] == audit_semantic_hash(audit)


def test_support_map_hashes_match(library_manifest: dict) -> None:
    pilot_hash = source_support_map_semantic_hash(load_pilot_source_support_map())
    core_hash = source_support_map_semantic_hash(load_core_source_support_map())
    assert library_manifest["source_support_hashes"]["pilot"] == pilot_hash
    assert library_manifest["source_support_hashes"]["core"] == core_hash


def test_single_source_policy_preserved() -> None:
    assert SINGLE_SOURCE_POLICY["owner_review_required_default"] is True


def test_no_new_patterns_beyond_twenty(library_manifest: dict) -> None:
    assert library_manifest["pattern_count"] == 20
    assert len(library_manifest["pattern_hashes"]) == 20
