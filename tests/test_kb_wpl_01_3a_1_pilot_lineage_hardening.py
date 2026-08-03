"""KB-WPL-01.3A.1 — Pilot lineage hardening tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from app.knowledge.workflow_patterns.contracts import SINGLE_SOURCE_POLICY, ManualAuditRecord
from app.knowledge.workflow_patterns.serialization import (
    audit_semantic_hash,
    load_pilot_audit_records,
    load_pilot_manifest,
    load_pilot_patterns,
    load_pilot_practice_index,
    load_pilot_practices,
    load_pilot_source_support_map,
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
)

REPO = Path(__file__).resolve().parents[1]
WPL_MODULE = REPO / "app" / "knowledge" / "workflow_patterns"
CATALOG_PATH = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "catalog.json"
CATALOG_MANIFEST_PATH = (
    REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "freeze_manifest.json"
)
FROZEN_CATALOG_HASH = "5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa"
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "subprocess", "socket")
PLACEHOLDER_RE = re.compile(r"placeholder|TODO|TBD|pending_practice", re.I)
ARCHIVE_CLAIMED_TESTED = re.compile(
    r"подтверждено|confirmed in prod|tested in prod|✅",
    re.I,
)


@pytest.fixture
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def patterns() -> list[dict]:
    return load_pilot_patterns()


@pytest.fixture
def practices() -> list[dict]:
    return load_pilot_practices()


@pytest.fixture
def support_map() -> dict:
    return load_pilot_source_support_map()


@pytest.fixture
def audit_records() -> list[dict]:
    return load_pilot_audit_records()


def test_01_no_placeholder_practice_ids(patterns: list[dict]) -> None:
    for pattern in patterns:
        practice_ids = pattern.get("source_practice_ids") or []
        assert practice_ids, f"{pattern['pattern_id']} missing practice lineage"
        for practice_id in practice_ids:
            assert not PLACEHOLDER_RE.search(practice_id)


def test_02_every_source_practice_id_resolves(patterns: list[dict], practices: list[dict]) -> None:
    known = {practice["practice_id"] for practice in practices}
    for pattern in patterns:
        for practice_id in pattern["source_practice_ids"]:
            assert practice_id in known


def test_03_every_practice_validates_against_schema(practices: list[dict]) -> None:
    for practice in practices:
        validate_practice_record(practice)


def test_04_practice_provenance_has_archive_or_internal_source(practices: list[dict]) -> None:
    allowed_archives = {
        "arc-skills-dlya-peredachi",
        "arc-bots-knowledge-rar",
        "marketsynth-accepted-internal",
    }
    for practice in practices:
        refs = practice.get("source_references") or []
        assert refs, practice["practice_id"]
        assert any(ref.get("archive_id") in allowed_archives for ref in refs)


def test_05_archive_tested_wording_not_auto_reproduced(practices: list[dict]) -> None:
    for practice in practices:
        blob = json.dumps(practice, ensure_ascii=False)
        if ARCHIVE_CLAIMED_TESTED.search(blob):
            assert practice["verification_status"] != "reproduced"


def test_06_regression_tested_practice_has_test_reference(practices: list[dict]) -> None:
    for practice in practices:
        if practice["verification_status"] == "regression_tested":
            env = practice.get("tested_environment", "")
            assert env.startswith("tests/")


def test_07_every_pattern_has_support_map_entry(patterns: list[dict], support_map: dict) -> None:
    mapped = {entry["pattern_id"] for entry in support_map["entries"]}
    for pattern in patterns:
        assert pattern["pattern_id"] in mapped


def test_08_pattern_lineage_minimum(patterns: list[dict], support_map: dict) -> None:
    for pattern in patterns:
        entry = next(e for e in support_map["entries"] if e["pattern_id"] == pattern["pattern_id"])
        has_two_workflows = len(entry["source_workflow_ids"]) >= 2
        has_practices = bool(entry["source_practice_ids"])
        has_audit = bool(entry.get("manual_audit_id"))
        assert has_two_workflows or (has_practices and has_audit)
        assert len(pattern["source_workflow_ids"]) >= 2


def test_09_support_signal_references_catalog_workflow(support_map: dict, catalog: dict) -> None:
    index = {item["workflow_template_id"] for item in catalog["templates"]}
    for entry in support_map["entries"]:
        for signal in entry["supporting_signals"]:
            assert signal["source_workflow_id"] in index


def test_10_support_signal_has_supported_pattern_rule(support_map: dict) -> None:
    for entry in support_map["entries"]:
        for signal in entry["supporting_signals"]:
            assert signal.get("supported_pattern_rule")


def test_11_support_signal_has_evidence_hash(support_map: dict) -> None:
    for entry in support_map["entries"]:
        for signal in entry["supporting_signals"]:
            assert len(signal.get("evidence_hash", "")) == 64


def test_12_no_raw_nodes_in_support_map(support_map: dict) -> None:
    blob = json.dumps(support_map)
    assert '"nodes"' not in blob
    assert "pinData" not in blob


def test_13_no_raw_connections_in_support_map(support_map: dict) -> None:
    blob = json.dumps(support_map)
    assert '"connections"' not in blob


def test_14_no_credential_values_in_support_map(support_map: dict) -> None:
    blob = json.dumps(support_map).lower()
    assert "credential_id" not in blob
    assert "api_key" not in blob


def test_15_one_workflow_may_support_multiple_patterns(support_map: dict) -> None:
    workflow_counts: dict[str, int] = {}
    for entry in support_map["entries"]:
        for source_id in entry["source_workflow_ids"]:
            workflow_counts[source_id] = workflow_counts.get(source_id, 0) + 1
    assert any(count > 1 for count in workflow_counts.values())


def test_16_multi_pattern_support_is_pattern_specific(support_map: dict) -> None:
    shared = "wf-353be45a7de607a0"
    entries = [e for e in support_map["entries"] if shared in e["source_workflow_ids"]]
    assert len(entries) >= 2
    rules = {
        signal["supported_pattern_rule"]
        for entry in entries
        for signal in entry["supporting_signals"]
        if signal["source_workflow_id"] == shared
    }
    assert len(rules) >= 2


def test_17_single_source_future_policy_requires_signoff() -> None:
    assert SINGLE_SOURCE_POLICY["owner_review_required_default"] is True
    allowed = SINGLE_SOURCE_POLICY["allowed_when"]
    assert "owner or delegated architecture reviewer signs the audit record" in allowed


def test_18_publication_practice_preserves_approval(practices: list[dict]) -> None:
    practice = next(
        p
        for p in practices
        if p["practice_id"] == "human_approval_before_write_or_publication"
    )
    assert "approval" in practice["recommended_practice"].lower()


def test_19_retry_practice_preserves_idempotency(practices: list[dict]) -> None:
    practice = next(p for p in practices if p["practice_id"] == "idempotency_before_retry")
    rec = practice["recommended_practice"].lower()
    assert "idempot" in rec or "dedup" in rec


def test_20_unknown_outcome_practice_forbids_auto_retry(practices: list[dict]) -> None:
    practice = next(
        p for p in practices if p["practice_id"] == "unknown_outcome_write_no_auto_retry"
    )
    blob = practice["recommended_practice"].lower()
    assert "auto-retry" in blob or "never auto-retry" in blob


def test_21_rag_practice_preserves_source_references(practices: list[dict]) -> None:
    practice = next(p for p in practices if p["practice_id"] == "evidence_grounded_generation")
    assert "source" in practice["recommended_practice"].lower()


def test_22_prompt_injection_practice_explicit(practices: list[dict]) -> None:
    practice = next(p for p in practices if p["practice_id"] == "prompt_injection_boundary")
    title = practice["title"].lower()
    rec = practice["recommended_practice"].lower()
    assert "injection" in title or "injection" in rec


def test_23_audit_records_have_reviewer_role_and_method(audit_records: list[dict]) -> None:
    for audit in audit_records:
        assert audit.get("reviewer_role")
        assert audit.get("review_method")


def test_24_owner_review_remains_required(audit_records: list[dict]) -> None:
    assert all(audit.get("owner_review_required") is True for audit in audit_records)


def test_25_practice_hashes_deterministic(practices: list[dict]) -> None:
    index = load_pilot_practice_index()
    for practice in practices:
        assert index["practice_hashes"][practice["practice_id"]] == practice_semantic_hash(practice)


def test_26_source_support_map_hash_deterministic(support_map: dict) -> None:
    manifest = load_pilot_manifest()
    assert manifest["source_support_map_hash"] == source_support_map_semantic_hash(support_map)


def test_27_pilot_bundle_hash_deterministic(patterns: list[dict]) -> None:
    manifest = load_pilot_manifest()
    for pattern in patterns:
        assert manifest["pattern_hashes"][pattern["pattern_id"]] == pattern_semantic_hash(pattern)
    assert manifest["semantic_hash"] == pilot_semantic_hash(manifest)


def test_28_frozen_catalog_hash_unchanged() -> None:
    manifest = json.loads(CATALOG_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["bundle_hash"] == FROZEN_CATALOG_HASH


def test_29_frozen_schema_hash_unchanged() -> None:
    assert recompute_bundle_hash() == FROZEN_BUNDLE_HASH


def test_30_existing_03a_tests_remain_compatible(audit_records: list[dict]) -> None:
    for audit in audit_records:
        record = ManualAuditRecord.model_validate(audit)
        assert record.audit_hash == audit_semantic_hash(audit)
        assert record.decision == "approved_for_pilot"


def test_31_no_workflow_execution_or_network() -> None:
    for path in WPL_MODULE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in FORBIDDEN_IMPORTS
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS


def test_32_frozen_skill_hashes_unchanged() -> None:
    from app.skills.hashing import calculate_skill_package_hash

    for skill_id, expected in KB_SKILL_PACKAGE_HASHES.items():
        root = REPO / "packages" / "skills" / skill_id
        assert calculate_skill_package_hash(root) == expected
