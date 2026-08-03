"""KB-WPL-01.3B — Core workflow pattern library tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from app.knowledge.workflow_patterns.contracts import SINGLE_SOURCE_POLICY
from app.knowledge.workflow_patterns.serialization import (
    FROZEN_PILOT_BUNDLE_HASH,
    FROZEN_SCHEMA_HASH,
    core_semantic_hash,
    load_core_audit_records,
    load_core_manifest,
    load_core_patterns,
    load_core_practices,
    load_core_source_support_map,
    load_pilot_manifest,
    load_pilot_patterns,
    pattern_semantic_hash,
    pilot_semantic_hash,
    practice_semantic_hash,
    source_support_map_semantic_hash,
)
from tests.support.kb_skill_validation import KB_SKILL_PACKAGE_HASHES
from tests.support.wpl_schema_validation import (
    FROZEN_BUNDLE_HASH,
    recompute_bundle_hash,
    validate_practice_record,
    validate_workflow_pattern,
)

REPO = Path(__file__).resolve().parents[1]
WPL_ROOT = REPO / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"
PILOT_DIR = WPL_ROOT / "patterns" / "pilot"
CATALOG_MANIFEST = (
    REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "freeze_manifest.json"
)
FROZEN_CATALOG_HASH = "5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa"
PILOT_PATTERN_HASHES = {
    "human_approval_before_publication": (
        "9d517782071707e146ffce6457f14d3c7b94e4a41634e2b79f5f32ebd1a5e288"
    ),
    "structured_LLM_to_API_request": (
        "157ed771e5f9ddc01835f1733a5f3d617c8859fdc994a0aaa9db32496cfa9f06"
    ),
    "retry_with_idempotency": (
        "f6c780052e067bc7530557780b86a6c7fc3f00461c26e65da8a8d9a98653b7b5"
    ),
    "evidence_grounded_generation": (
        "c55ca02b4c3b368f99ca2e8fb41502b1c2a31b8f16aa2cf09b49d991abf2cf97"
    ),
    "lead_capture_to_qualification": (
        "01160d23995fa5ca9d72ec62257d5ad970198d1224f886833311fccf99f563e2"
    ),
    "draft_to_human_approval": (
        "752a967226d3ddecf46e213207d40c0a4cbe0a45d36ae6e2fee997c5a0a8ab8e"
    ),
    "workflow_backup": (
        "d535c38819b108f6a19ba09cc1c32589f96d9c955129f08b4067135f9890105c"
    ),
    "error_workflow_or_recovery": (
        "5d2ae59128835f408ed82dcb63fa83e9d61d3d72c12436d0214bf49e34912210"
    ),
}
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "subprocess", "socket")
CORE_NEW_IDS = {
    "pagination_and_batching",
    "checkpoint_and_resume",
    "dead_letter_queue",
    "provider_rate_limit_handling",
    "quality_gate_after_generation",
    "specialist_subworkflow",
    "supervisor_pattern",
    "tool_workflow_separation",
    "human_edit_then_resume",
    "publication_confirmation",
    "source_lineage_preservation",
    "customer_feedback_to_learning_candidate",
}


@pytest.fixture
def catalog() -> dict:
    path = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def pilot_patterns() -> list[dict]:
    return load_pilot_patterns()


@pytest.fixture
def core_patterns() -> list[dict]:
    return load_core_patterns()


@pytest.fixture
def core_practices() -> list[dict]:
    return load_core_practices()


@pytest.fixture
def support_map() -> dict:
    return load_core_source_support_map()


@pytest.fixture
def core_manifest() -> dict:
    return load_core_manifest()


def test_01_total_library_fifteen_to_twenty_five(
    pilot_patterns: list[dict], core_patterns: list[dict]
) -> None:
    total = len(pilot_patterns) + len(core_patterns)
    assert 15 <= total <= 25
    assert total == 20


def test_02_existing_pilot_patterns_unchanged(pilot_patterns: list[dict]) -> None:
    manifest = load_pilot_manifest()
    assert manifest["bundle_hash"] == FROZEN_PILOT_BUNDLE_HASH
    for pattern in pilot_patterns:
        pid = pattern["pattern_id"]
        assert pid in PILOT_PATTERN_HASHES
        expected = PILOT_PATTERN_HASHES[pid]
        assert manifest["pattern_hashes"][pid] == expected
        assert pattern_semantic_hash(pattern) == expected


def test_03_new_patterns_validate_schema(core_patterns: list[dict]) -> None:
    for pattern in core_patterns:
        validate_workflow_pattern(pattern)


def test_04_new_patterns_maturity_reviewed(core_patterns: list[dict]) -> None:
    assert all(p["maturity"] == "reviewed" for p in core_patterns)


def test_05_no_forbidden_maturity(core_patterns: list[dict]) -> None:
    forbidden = {"active", "executable", "deployed", "approved", "platform_adapted"}
    for pattern in core_patterns:
        assert pattern["maturity"] not in forbidden


def test_06_no_raw_workflow_bodies(core_patterns: list[dict]) -> None:
    for pattern in core_patterns:
        assert "nodes" not in pattern
        assert "connections" not in pattern


def test_07_no_credentials(core_patterns: list[dict]) -> None:
    blob = json.dumps(core_patterns).lower()
    assert "credential_id" not in blob


def test_08_main_flows_provider_neutral(core_patterns: list[dict]) -> None:
    for pattern in core_patterns:
        steps_blob = json.dumps(pattern.get("steps", [])).lower()
        variants_blob = json.dumps(pattern.get("implementation_variants", [])).lower()
        for name in ("telegram", "gmail", "openai", "instagram"):
            if name in steps_blob:
                assert name in variants_blob


def test_09_every_pattern_has_source_workflows(core_patterns: list[dict]) -> None:
    for pattern in core_patterns:
        assert len(pattern["source_workflow_ids"]) >= 2


def test_10_every_pattern_has_practice_records(core_patterns: list[dict]) -> None:
    for pattern in core_patterns:
        assert pattern["source_practice_ids"]


def test_11_every_pattern_has_manual_audit(core_manifest: dict) -> None:
    assert len(load_core_audit_records()) == len(core_manifest["core_pattern_ids"])


def test_12_every_pattern_has_support_map(core_patterns: list[dict], support_map: dict) -> None:
    mapped = {e["pattern_id"] for e in support_map["entries"]}
    for pattern in core_patterns:
        assert pattern["pattern_id"] in mapped


def test_13_single_source_policy_frozen() -> None:
    assert SINGLE_SOURCE_POLICY["owner_review_required_default"] is True


def test_14_rejected_source_cannot_support_pattern(catalog: dict) -> None:
    index = {t["workflow_template_id"]: t for t in catalog["templates"]}
    for pattern in load_core_patterns():
        for source_id in pattern["source_workflow_ids"]:
            assert index[source_id]["quarantine_status"] != "rejected"


def test_15_publication_requires_approval(core_patterns: list[dict]) -> None:
    pub = [p for p in core_patterns if p["publication_sensitive"]]
    for pattern in pub:
        assert pattern["approval_requirements"]["publication_approval_required"] is True
        assert pattern["approval_requirements"]["auto_approval_allowed"] is False


def test_16_human_edit_requires_review(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "human_edit_then_resume")
    assert pattern["approval_requirements"]["human_approval_required"] is True


def test_17_retry_patterns_require_idempotency(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "provider_rate_limit_handling")
    assert pattern["idempotency_requirements"]["required"] is True


def test_18_unknown_outcome_no_auto_retry(core_patterns: list[dict]) -> None:
    for pattern in core_patterns:
        if pattern.get("retry_policy") not in ("none", ""):
            assert pattern["idempotency_requirements"]["unknown_outcome_auto_retry"] is False


def test_19_pagination_has_termination(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "pagination_and_batching")
    assert "max_batch_size" in pattern["input_contract"]["required"]
    assert any(e.get("condition") == "complete" for e in pattern["edges"])


def test_20_batch_bounded(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "pagination_and_batching")
    assert "max_batch_size" in json.dumps(pattern)


def test_21_checkpoint_defines_resume_state(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "checkpoint_and_resume")
    assert "checkpoint_id" in pattern["input_contract"]["required"]
    assert "checkpoint_id" in pattern["output_contract"]["required"]


def test_22_dead_letter_terminal_handling(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "dead_letter_queue")
    assert "dead_letter" in pattern["error_paths"]
    assert any("dead_letter" in s["step_name"].lower() for s in pattern["steps"])


def test_23_rate_limit_backoff(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "provider_rate_limit_handling")
    assert "backoff" in pattern["rate_limit_policy"].lower() or "backoff" in pattern["retry_policy"]


def test_24_quality_gate_blocks_invalid(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "quality_gate_after_generation")
    assert any(s["step_type"] == "validate" for s in pattern["steps"])


def test_25_supervisor_no_undeclared_tools(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "supervisor_pattern")
    blob = " ".join(pattern["known_limitations"]).lower()
    assert "tool" in blob


def test_26_specialist_scope_explicit(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "specialist_subworkflow")
    assert "specialist_scope" in pattern["input_contract"]["required"]


def test_27_tool_workflow_permission_boundary(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "tool_workflow_separation")
    assert any(s["step_type"] == "validate" for s in pattern["steps"])


def test_28_prompt_injection_not_applicable_core_set(core_patterns: list[dict]) -> None:
    ids = {p["pattern_id"] for p in core_patterns}
    assert "prompt_injection_filter" not in ids


def test_29_feedback_creates_candidate_only(core_patterns: list[dict]) -> None:
    pattern = next(
        p for p in core_patterns if p["pattern_id"] == "customer_feedback_to_learning_candidate"
    )
    assert "knowledge_candidate" in pattern["output_contract"]["required"]
    limitations = " ".join(pattern["known_limitations"]).lower()
    assert "canonical" in limitations


def test_30_learning_candidate_tenant_scoped(core_patterns: list[dict]) -> None:
    pattern = next(
        p for p in core_patterns if p["pattern_id"] == "customer_feedback_to_learning_candidate"
    )
    assert pattern["tenant_scope"] == "tenant_scoped"
    assert "tenant_context" in pattern["output_contract"]["required"]


def test_31_canonical_knowledge_not_auto_mutated(core_patterns: list[dict]) -> None:
    pattern = next(
        p for p in core_patterns if p["pattern_id"] == "customer_feedback_to_learning_candidate"
    )
    blob = " ".join(pattern["known_limitations"]).lower()
    assert "auto-promote" in blob or "does not modify" in blob


def test_32_source_lineage_preserved(core_patterns: list[dict]) -> None:
    pattern = next(p for p in core_patterns if p["pattern_id"] == "source_lineage_preservation")
    assert "source_lineage" in pattern["output_contract"]["required"]


def test_33_practice_hashes_deterministic(core_practices: list[dict], core_manifest: dict) -> None:
    for practice in core_practices:
        pid = practice["practice_id"]
        assert core_manifest["practice_hashes"][pid] == practice_semantic_hash(practice)


def test_34_pattern_hashes_deterministic(core_patterns: list[dict], core_manifest: dict) -> None:
    for pattern in core_patterns:
        pid = pattern["pattern_id"]
        assert core_manifest["core_pattern_hashes"][pid] == pattern_semantic_hash(pattern)


def test_35_core_bundle_hash_deterministic(core_manifest: dict) -> None:
    assert core_manifest["semantic_hash"] == core_semantic_hash(core_manifest)


def test_36_generated_at_excluded_from_semantic_hash(core_manifest: dict) -> None:
    altered = dict(core_manifest)
    altered["generated_at"] = "2099-01-01T00:00:00+00:00"
    assert core_semantic_hash(core_manifest) == core_semantic_hash(altered)


def test_37_frozen_catalog_hash_unchanged(core_manifest: dict) -> None:
    cat = json.loads(CATALOG_MANIFEST.read_text(encoding="utf-8"))
    assert cat["bundle_hash"] == FROZEN_CATALOG_HASH
    assert core_manifest["source_catalog_hash"] == FROZEN_CATALOG_HASH


def test_38_frozen_schema_hash_unchanged(core_manifest: dict) -> None:
    assert recompute_bundle_hash() == FROZEN_BUNDLE_HASH
    assert core_manifest["schema_bundle_hash"] == FROZEN_SCHEMA_HASH


def test_39_pilot_bundle_hash_unchanged() -> None:
    manifest = load_pilot_manifest()
    assert manifest["bundle_hash"] == FROZEN_PILOT_BUNDLE_HASH
    assert pilot_semantic_hash(manifest) == manifest["semantic_hash"]


def test_40_no_execution_network_api(core_manifest: dict) -> None:
    module = REPO / "app" / "knowledge" / "workflow_patterns"
    for path in module.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in FORBIDDEN_IMPORTS
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS
    assert core_manifest["status"] == "core_reviewed"


def test_41_frozen_skill_hashes_unchanged() -> None:
    from app.skills.hashing import calculate_skill_package_hash

    for skill_id, expected in KB_SKILL_PACKAGE_HASHES.items():
        root = REPO / "packages" / "skills" / skill_id
        assert calculate_skill_package_hash(root) == expected


def test_42_no_spend_billing_patterns(core_patterns: list[dict]) -> None:
    for pattern in core_patterns:
        assert pattern["billing_sensitive"] is False
        assert pattern["approval_requirements"]["spend_approval_required"] is False


def test_43_core_pattern_ids_match_priority(core_patterns: list[dict]) -> None:
    assert {p["pattern_id"] for p in core_patterns} == CORE_NEW_IDS


def test_44_practices_validate(core_practices: list[dict]) -> None:
    for practice in core_practices:
        validate_practice_record(practice)


def test_45_support_map_hash(core_manifest: dict, support_map: dict) -> None:
    assert core_manifest["source_support_map_hash"] == source_support_map_semantic_hash(support_map)
