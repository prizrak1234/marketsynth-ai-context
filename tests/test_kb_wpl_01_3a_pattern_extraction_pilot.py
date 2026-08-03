"""KB-WPL-01.3A — Workflow pattern extraction pilot tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from app.knowledge.workflow_patterns.contracts import ManualAuditRecord
from app.knowledge.workflow_patterns.serialization import (
    load_pilot_audit_records,
    load_pilot_manifest,
    load_pilot_patterns,
    pattern_semantic_hash,
    pilot_semantic_hash,
)
from app.knowledge.workflow_patterns.source_support import validate_pattern_source_support
from app.knowledge.workflow_patterns.validation import (
    validate_pattern_semantics,
    validate_pilot_pattern,
)
from tests.support.kb_skill_validation import KB_SKILL_PACKAGE_HASHES
from tests.support.wpl_schema_validation import (
    FROZEN_BUNDLE_HASH,
    recompute_bundle_hash,
    validate_workflow_pattern,
    validate_workflow_pattern_semantics,
)

REPO = Path(__file__).resolve().parents[1]
WPL_MODULE = REPO / "app" / "knowledge" / "workflow_patterns"
CATALOG_PATH = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "catalog.json"
CATALOG_MANIFEST_PATH = (
    REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "freeze_manifest.json"
)
FROZEN_CATALOG_HASH = "5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa"
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "subprocess", "socket")


@pytest.fixture
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def audit_records() -> list[ManualAuditRecord]:
    return [ManualAuditRecord.model_validate(item) for item in load_pilot_audit_records()]


@pytest.fixture
def patterns() -> list[dict]:
    return load_pilot_patterns()


def test_01_pilot_contains_six_to_eight_patterns(patterns: list[dict]) -> None:
    assert 6 <= len(patterns) <= 8


def test_02_every_pattern_validates_against_schema(patterns: list[dict]) -> None:
    for pattern in patterns:
        validate_workflow_pattern(pattern)


def test_03_every_pattern_maturity_reviewed(patterns: list[dict]) -> None:
    assert all(pattern["maturity"] == "reviewed" for pattern in patterns)


def test_04_no_forbidden_maturity(patterns: list[dict]) -> None:
    forbidden = {"active", "executable", "deployed", "approved"}
    for pattern in patterns:
        assert pattern["maturity"] not in forbidden


def test_05_no_raw_nodes(patterns: list[dict]) -> None:
    for pattern in patterns:
        assert "nodes" not in pattern


def test_06_no_raw_connections(patterns: list[dict]) -> None:
    for pattern in patterns:
        assert "connections" not in pattern


def test_07_no_credential_ids(patterns: list[dict]) -> None:
    blob = json.dumps(patterns)
    assert "credential_id" not in blob.lower()


def test_08_no_raw_secrets(patterns: list[dict]) -> None:
    blob = json.dumps(patterns)
    assert "sk-" not in blob
    assert "Bearer " not in blob


def test_09_main_patterns_provider_neutral(patterns: list[dict]) -> None:
    for pattern in patterns:
        assert not validate_pattern_semantics(pattern)


def test_10_provider_names_in_variants_only(patterns: list[dict]) -> None:
    for pattern in patterns:
        variants = json.dumps(pattern.get("implementation_variants", [])).lower()
        steps = json.dumps(pattern.get("steps", [])).lower()
        for provider in ("telegram", "gmail", "wordpress", "instagram"):
            if provider in steps:
                assert provider in variants


def test_11_every_pattern_has_source_ids(patterns: list[dict]) -> None:
    for pattern in patterns:
        assert pattern.get("source_workflow_ids")


def test_12_every_source_in_catalog(patterns: list[dict], catalog: dict) -> None:
    index = {item["workflow_template_id"] for item in catalog["templates"]}
    for pattern in patterns:
        for source_id in pattern["source_workflow_ids"]:
            assert source_id in index


def test_13_source_hashes_match_catalog(patterns: list[dict], catalog: dict) -> None:
    manifest = load_pilot_manifest()
    index = {item["workflow_template_id"]: item for item in catalog["templates"]}
    for source_id, expected in manifest["source_workflow_hashes"].items():
        assert index[source_id]["workflow_hash"] == expected


def test_14_two_source_gate_passes(patterns: list[dict], catalog: dict, audit_records) -> None:
    pattern = next(p for p in patterns if len(p["source_workflow_ids"]) >= 2)
    result = validate_pattern_source_support(pattern, catalog, audit_records)
    assert result.supported
    assert result.support_mode == "two_source"


def test_15_single_source_requires_manual_audit(catalog: dict) -> None:
    pattern = {
        "pattern_id": "test_single",
        "source_workflow_ids": ["wf-353be45a7de607a0"],
    }
    result = validate_pattern_source_support(pattern, catalog, [])
    assert not result.supported
    audit = ManualAuditRecord(
        audit_id="audit-test-single",
        workflow_template_ids=["wf-353be45a7de607a0"],
        pattern_ids=["test_single"],
        decision="approved_for_pilot",
        rationale="Pilot test audit for single-source gate.",
    )
    result2 = validate_pattern_source_support(pattern, catalog, [audit])
    assert result2.supported
    assert result2.support_mode == "single_source_audited"


def test_16_zero_source_rejected(catalog: dict, audit_records) -> None:
    result = validate_pattern_source_support(
        {"pattern_id": "empty", "source_workflow_ids": []},
        catalog,
        audit_records,
    )
    assert not result.supported


def test_17_rejected_source_blocked(catalog: dict, audit_records) -> None:
    pattern = {
        "pattern_id": "bad",
        "source_workflow_ids": ["wf-does-not-exist"],
    }
    result = validate_pattern_source_support(pattern, catalog, audit_records)
    assert not result.supported


def test_18_critical_source_blocked(catalog: dict, audit_records) -> None:
    template = catalog["templates"][0].copy()
    template["workflow_template_id"] = "wf-critical-test"
    template["security_findings"] = [
        {
            "finding_id": "sf1",
            "severity": "critical",
            "finding_type": "destructive_sql",
            "location": "body",
            "description": "x",
            "redacted": True,
            "provenance": {"source_type": "x", "archive_id": "arc"},
        }
    ]
    bad_catalog = {
        "templates": [*catalog["templates"], template],
    }
    pattern = {"pattern_id": "crit", "source_workflow_ids": ["wf-critical-test"]}
    result = validate_pattern_source_support(pattern, bad_catalog, audit_records)
    assert not result.supported


def test_19_publication_requires_approval(patterns: list[dict]) -> None:
    pub = next(p for p in patterns if p["publication_sensitive"])
    assert pub["approval_requirements"]["publication_approval_required"] is True


def test_20_publication_auto_approval_rejected(patterns: list[dict]) -> None:
    for pattern in patterns:
        if pattern["publication_sensitive"]:
            assert pattern["approval_requirements"]["auto_approval_allowed"] is False


def test_21_publication_requires_evidence(patterns: list[dict]) -> None:
    pub = next(p for p in patterns if p["publication_sensitive"])
    assert pub["evidence_requirements"]["required"] is True


def test_22_draft_to_approval_preserves_decision(patterns: list[dict]) -> None:
    pattern = next(p for p in patterns if p["pattern_id"] == "draft_to_human_approval")
    steps = {step["step_id"]: step for step in pattern["steps"]}
    assert steps["s3"]["step_name"].lower().find("decision") >= 0 or any(
        edge.get("condition") == "decision_recorded" for edge in pattern["edges"]
    )


def test_23_retry_requires_idempotency(patterns: list[dict]) -> None:
    pattern = next(p for p in patterns if p["pattern_id"] == "retry_with_idempotency")
    assert pattern["idempotency_requirements"]["required"] is True


def test_24_unknown_outcome_no_auto_retry(patterns: list[dict]) -> None:
    pattern = next(p for p in patterns if p["pattern_id"] == "retry_with_idempotency")
    assert pattern["idempotency_requirements"]["unknown_outcome_auto_retry"] is False


def test_25_duplicate_prevention_represented(patterns: list[dict]) -> None:
    pattern = next(p for p in patterns if p["pattern_id"] == "retry_with_idempotency")
    assert pattern["idempotency_requirements"]["duplicate_event_prevention"] is True


def test_26_rag_preserves_source_references(patterns: list[dict]) -> None:
    pattern = next(p for p in patterns if p["pattern_id"] == "evidence_grounded_generation")
    assert "source_reference" in pattern["evidence_requirements"]["evidence_classes"]


def test_27_rag_injection_boundary(patterns: list[dict]) -> None:
    pattern = next(p for p in patterns if p["pattern_id"] == "evidence_grounded_generation")
    blob = " ".join(pattern["known_limitations"]).lower()
    assert "injection" in blob


def test_28_structured_llm_requires_validation(patterns: list[dict]) -> None:
    pattern = next(p for p in patterns if p["pattern_id"] == "structured_LLM_to_API_request")
    assert any(step["step_type"] == "validate" for step in pattern["steps"])


def test_29_error_recovery_path_present(patterns: list[dict]) -> None:
    pattern = next(p for p in patterns if p["pattern_id"] == "error_workflow_or_recovery")
    assert pattern["error_paths"]


def test_30_tenant_context_preserved(patterns: list[dict]) -> None:
    for pattern in patterns:
        assert pattern["tenant_scope"] == "tenant_scoped"
        assert "tenant_context" in pattern["input_contract"]["required"]


def test_31_quality_gates_complete(patterns: list[dict]) -> None:
    for pattern in patterns:
        assert len(pattern["quality_gates"]) >= 11


def test_32_limitations_present(patterns: list[dict]) -> None:
    for pattern in patterns:
        assert pattern["known_limitations"]


def test_33_pattern_hash_deterministic(patterns: list[dict]) -> None:
    manifest = load_pilot_manifest()
    for pattern in patterns:
        assert manifest["pattern_hashes"][pattern["pattern_id"]] == pattern_semantic_hash(pattern)


def test_34_pilot_bundle_hash_deterministic() -> None:
    manifest = load_pilot_manifest()
    assert manifest["bundle_hash"]
    assert manifest["semantic_hash"] == pilot_semantic_hash(manifest)


def test_35_generated_at_excluded_from_semantic_hash() -> None:
    manifest = load_pilot_manifest()
    altered = dict(manifest)
    altered["generated_at"] = "2099-01-01T00:00:00+00:00"
    assert pilot_semantic_hash(manifest) == pilot_semantic_hash(altered)


def test_36_frozen_catalog_hash_unchanged() -> None:
    manifest = json.loads(CATALOG_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["bundle_hash"] == FROZEN_CATALOG_HASH


def test_37_frozen_wpl_schema_hash_unchanged() -> None:
    assert recompute_bundle_hash() == FROZEN_BUNDLE_HASH


def test_38_no_workflow_execution() -> None:
    parser = (REPO / "app" / "knowledge" / "workflow_catalog" / "parser.py").read_text(
        encoding="utf-8"
    )
    assert "subprocess" not in parser


def test_39_no_network_imports_in_pattern_module() -> None:
    for path in WPL_MODULE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in FORBIDDEN_IMPORTS
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS


def test_40_existing_wpl_tests_remain_compatible(patterns: list[dict]) -> None:
    for pattern in patterns:
        validate_workflow_pattern(pattern)
        assert not validate_workflow_pattern_semantics(pattern)
        report = validate_pilot_pattern(
            pattern,
            catalog=json.loads(CATALOG_PATH.read_text(encoding="utf-8")),
            audit_records=[
                ManualAuditRecord.model_validate(item) for item in load_pilot_audit_records()
            ],
            schema_validate=validate_workflow_pattern,
        )
        assert report.schema_valid
        assert not report.semantic_errors


def test_41_frozen_skill_hashes_unchanged() -> None:
    from app.skills.hashing import calculate_skill_package_hash

    for skill_id, expected in KB_SKILL_PACKAGE_HASHES.items():
        root = REPO / "packages" / "skills" / skill_id
        assert calculate_skill_package_hash(root) == expected
