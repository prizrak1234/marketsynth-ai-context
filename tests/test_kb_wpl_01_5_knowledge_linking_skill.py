"""KB-WPL-01.5 — Knowledge Linking Skill tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from app.audit.adapters import adapt_package_validation_report
from app.knowledge.knowledge_linking.contradiction_detection import detect_contradiction_candidates
from app.knowledge.knowledge_linking.duplicate_detection import (
    classify_provider_variants,
    detect_duplicate_candidates,
)
from app.knowledge.knowledge_linking.errors import GENERIC_NOT_FOUND
from app.knowledge.knowledge_linking.orphan_detection import (
    collect_linked_artifact_ids,
    detect_orphan_artifacts,
    is_standalone_exempt,
)
from app.knowledge.knowledge_linking.relations import ALLOWED_RELATION_TYPES
from app.knowledge.knowledge_linking.serialization import build_artifact_index
from app.knowledge.knowledge_linking.supersession import detect_supersession_candidates
from app.knowledge.knowledge_linking.validation import (
    detect_broken_links,
    detect_index_recommendations,
    validate_knowledge_link,
    validate_linking_output,
)
from app.knowledge.knowledge_linking.visibility import (
    filter_visible_artifacts,
    reject_cross_tenant_link,
    resolve_artifact,
)
from app.knowledge.n8n_engineering.constants import (
    FROZEN_LIBRARY_SEMANTIC_HASH,
    N8N_ENGINEERING_SKILL_IDS,
)
from app.knowledge.workflow_patterns.serialization import (
    FROZEN_PILOT_BUNDLE_HASH,
    FROZEN_SCHEMA_HASH,
    load_library_manifest,
)
from app.lineage.builders import build_package_validation_lineage
from app.schemas.contracts import SkillLifecycleStatus
from app.skills.hashing import calculate_skill_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from tests.support.kb_skill_validation import KB_SKILL_PACKAGE_HASHES
from tests.support.knowledge_linking_skill_validation import (
    load_json_fixture,
    package_hash,
    package_root,
    sample_link,
    sample_node,
    schema_validator,
)

REPO = Path(__file__).resolve().parents[1]
SKILL_ID = "ms.skill.knowledge_linking"
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "subprocess", "socket", "n8n")
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


@pytest.fixture
def package_report():
    return validate_skill_package(package_root())


def test_01_package_exists_and_validates(package_report) -> None:
    assert package_root().is_dir()
    assert package_report.valid is True


def test_02_version_010(package_report) -> None:
    assert package_report.skill_version == "0.1.0"


def test_03_status_candidate(package_report) -> None:
    projection = project_validation_report(package_report)
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_04_non_executable(package_report) -> None:
    assert package_report.manifest.activation_conditions.executable is False


def test_05_no_tools(package_report) -> None:
    assert package_report.manifest.allowed_tools == []


def test_06_network_denied(package_report) -> None:
    assert package_report.manifest.network_policy.default.value == "deny"


def test_07_scripts_disabled(package_report) -> None:
    assert package_report.manifest.script_policy.enabled is False


def test_08_output_contract_research(package_report) -> None:
    assert package_report.manifest.output_contract_type.value == "research"


def test_09_input_schema_valid() -> None:
    schema_validator("input.schema.json").validate(
        load_json_fixture("tests/fixtures/input_bounded_scope.json")
    )


def test_10_output_schema_valid() -> None:
    schema_validator("output.schema.json").validate(
        load_json_fixture("tests/fixtures/output_complete_report.json")
    )


def test_11_link_schema_valid() -> None:
    schema_validator("knowledge-link.schema.json").validate(sample_link("s1", "s2"))


def test_12_broken_link_schema_valid() -> None:
    broken = {
        "broken_link_id": "b1",
        "source_artifact_id": "s1",
        "expected_target_id": "missing",
        "relation_type": "depends_on",
        "failure_type": "missing_target",
        "observed_reference": {},
        "expected_reference": {},
        "severity": "high",
        "blocking": True,
        "remediation": "fix",
        "provenance": {},
    }
    schema_validator("broken-link.schema.json").validate(broken)


def test_13_duplicate_schema_valid() -> None:
    dup = {
        "duplicate_candidate_id": "d1",
        "artifact_ids": ["a1", "a2"],
        "duplicate_type": "exact_content",
        "evidence": [],
        "differences": [],
        "confidence": "high",
        "merge_recommended": False,
        "human_review_required": True,
        "provenance": {},
    }
    schema_validator("duplicate-candidate.schema.json").validate(dup)


def test_14_supersession_schema_valid() -> None:
    sup = {
        "candidate_id": "sup1",
        "older_artifact_id": "old",
        "newer_artifact_id": "new",
        "evidence": [],
        "compatibility_status": "compatible",
        "historical_resolution_required": True,
        "retirement_recommendation": "review_only",
        "confidence": "medium",
        "human_review_required": True,
        "provenance": {},
    }
    schema_validator("supersession-candidate.schema.json").validate(sup)


def test_15_contradiction_schema_valid() -> None:
    contra = {
        "contradiction_id": "c1",
        "artifact_ids": ["a1", "a2"],
        "contradiction_type": "contract_conflict",
        "statements_or_rules": [],
        "evidence": [],
        "severity": "high",
        "blocking": True,
        "resolution_owner": "human_reviewer",
        "recommended_resolution_process": "manual",
        "provenance": {},
    }
    schema_validator("contradiction-candidate.schema.json").validate(contra)


def test_16_index_recommendation_schema_valid() -> None:
    rec = {
        "recommendation_id": "r1",
        "index_type": "skill_matrix",
        "scope": "global",
        "missing_or_stale_artifacts": [],
        "proposed_index_entries": [],
        "rationale": "missing",
        "confidence": "high",
        "human_review_required": True,
        "provenance": {},
    }
    schema_validator("index-recommendation.schema.json").validate(rec)


def test_17_known_artifacts_link_successfully() -> None:
    artifacts = [
        sample_node("skill-a"),
        sample_node("pattern-b", artifact_type="workflow_pattern"),
    ]
    index = build_artifact_index(artifacts)
    link = sample_link("skill-a", "pattern-b", relation_type="uses_pattern")
    assert not validate_knowledge_link(link, artifact_index=index, tenant_id="tenant-alpha")


def test_18_unknown_target_rejected() -> None:
    index = build_artifact_index([sample_node("skill-a")])
    link = sample_link("skill-a", "missing-target")
    errors = validate_knowledge_link(link, artifact_index=index, tenant_id="tenant-alpha")
    assert "target_not_found" in errors


def test_19_invisible_target_generic_not_found() -> None:
    hidden = sample_node("hidden", tenant_scope="tenant-beta", tenant_id="tenant-beta")
    index = build_artifact_index([sample_node("skill-a"), hidden])
    resolved = resolve_artifact("hidden", index, tenant_id="tenant-alpha")
    assert resolved is None
    assert GENERIC_NOT_FOUND == "artifact_not_found"


def test_20_cross_tenant_link_rejected() -> None:
    source = sample_node("s1", tenant_scope="tenant-a", tenant_id="tenant-a")
    target = sample_node("t1", tenant_scope="tenant-b", tenant_id="tenant-b")
    link = sample_link("s1", "t1")
    rejected = reject_cross_tenant_link(link, source, target, tenant_id="tenant-a")
    assert rejected is not None
    assert rejected["reason"] == "cross_tenant_forbidden"


def test_21_global_artifact_can_be_linked() -> None:
    global_node = sample_node("global-pattern", tenant_scope="global")
    tenant_node = sample_node("tenant-skill", tenant_scope="tenant-a", tenant_id="tenant-a")
    index = build_artifact_index([global_node, tenant_node])
    link = sample_link("tenant-skill", "global-pattern")
    assert not validate_knowledge_link(link, artifact_index=index, tenant_id="tenant-a")


def test_22_project_private_mismatch_rejected() -> None:
    a = sample_node("a", tenant_scope="tenant-a", tenant_id="tenant-a", project_id="proj-1")
    b = sample_node("b", tenant_scope="tenant-a", tenant_id="tenant-a", project_id="proj-2")
    index = build_artifact_index([a, b])
    link = sample_link("a", "b")
    assert "project_private_mismatch" in validate_knowledge_link(
        link, artifact_index=index, tenant_id="tenant-a", project_id="proj-1"
    )


def test_23_high_confidence_without_evidence_rejected() -> None:
    index = build_artifact_index([sample_node("a"), sample_node("b")])
    link = sample_link("a", "b", confidence="high", evidence=[])
    assert "high_confidence_requires_deterministic_evidence" in validate_knowledge_link(
        link, artifact_index=index, tenant_id="tenant-alpha"
    )


def test_24_explicit_dependency_high_confidence() -> None:
    index = build_artifact_index([sample_node("a"), sample_node("b")])
    link = sample_link(
        "a",
        "b",
        evidence=[{"type": "declared_dependency", "manifest": "dependencies"}],
    )
    assert not validate_knowledge_link(link, artifact_index=index, tenant_id="tenant-alpha")


def test_25_exact_hash_duplicate_detected() -> None:
    artifacts = [
        sample_node("a1", content_hash=HASH_A, title="Doc A"),
        sample_node("a2", content_hash=HASH_A, title="Doc B"),
    ]
    dups = detect_duplicate_candidates(artifacts)
    assert any(d["duplicate_type"] == "exact_content" for d in dups)


def test_26_same_identity_version_different_hash_blocking() -> None:
    artifacts = [
        sample_node("a1", content_hash=HASH_A, title="Skill X", artifact_type="skill"),
        sample_node("a2", content_hash=HASH_B, title="Skill X", artifact_type="skill"),
    ]
    for artifact in artifacts:
        artifact["version"] = "0.1.0"
    dups = detect_duplicate_candidates(artifacts)
    assert any(d["duplicate_type"] == "identity_conflict" for d in dups)


def test_27_different_versions_not_exact_duplicates() -> None:
    artifacts = [
        sample_node("v1", content_hash=HASH_A, title="Skill X"),
        sample_node("v2", content_hash=HASH_B, title="Skill X"),
    ]
    artifacts[0]["version"] = "0.1.0"
    artifacts[1]["version"] = "0.2.0"
    dups = detect_duplicate_candidates(artifacts)
    assert not any(d["duplicate_type"] == "exact_content" for d in dups)


def test_28_provider_variants_classified_variant_of() -> None:
    artifacts = [
        sample_node("p1", provider_neutral_topology_id="topo-retry"),
        sample_node("p2", provider_neutral_topology_id="topo-retry"),
    ]
    variants = classify_provider_variants(artifacts)
    assert variants and variants[0]["relation_type"] == "variant_of"


def test_29_supersession_preserves_old_artifact() -> None:
    artifacts = [
        sample_node("old", logical_artifact_id="skill-x"),
        sample_node("new", logical_artifact_id="skill-x", supersedes=["old"]),
    ]
    artifacts[0]["version"] = "0.1.0"
    artifacts[1]["version"] = "0.2.0"
    candidates = detect_supersession_candidates(artifacts)
    assert candidates[0]["older_artifact_id"] == "old"
    assert candidates[0]["historical_resolution_required"] is True


def test_30_incompatible_supersession_visible() -> None:
    artifacts = [
        sample_node("old", logical_artifact_id="rfc-x"),
        sample_node(
            "new",
            logical_artifact_id="rfc-x",
            supersedes=["old"],
            compatibility_status="incompatible",
        ),
    ]
    artifacts[0]["version"] = "0.1.0"
    artifacts[1]["version"] = "1.0.0"
    candidates = detect_supersession_candidates(artifacts)
    assert candidates[0]["compatibility_status"] == "incompatible"


def test_31_contradiction_does_not_choose_winner() -> None:
    claim_required = {"claim_key": "retry", "value": "required", "domain": "sec"}
    claim_optional = {"claim_key": "retry", "value": "optional", "domain": "sec"}
    artifacts = [
        sample_node("rfc-a", declared_claims=[claim_required]),
        sample_node("rfc-b", declared_claims=[claim_optional]),
    ]
    contra = detect_contradiction_candidates(artifacts)
    assert contra[0]["resolution_owner"] == "human_reviewer"
    assert "manual_review_no_auto_winner" in contra[0]["recommended_resolution_process"]


def test_32_broken_pattern_id_detected() -> None:
    artifacts = [
        sample_node(
            "skill-1",
            declared_references=[
                {"target_artifact_id": "pattern-missing", "relation_type": "uses_pattern"}
            ],
        )
    ]
    broken = detect_broken_links(artifacts, tenant_id="tenant-alpha")
    assert broken[0]["failure_type"] == "missing_target"


def test_33_missing_practice_record_detected() -> None:
    artifacts = [
        sample_node(
            "pattern-1",
            artifact_type="workflow_pattern",
            declared_references=[
                {"target_artifact_id": "practice-missing", "relation_type": "uses_practice"}
            ],
        )
    ]
    broken = detect_broken_links(artifacts, tenant_id="tenant-alpha")
    assert broken[0]["failure_type"] == "missing_target"


def test_34_schema_hash_mismatch_blocking() -> None:
    target = sample_node("schema-1", content_hash=HASH_A)
    artifacts = [
        sample_node(
            "skill-1",
            declared_references=[
                {
                    "target_artifact_id": "schema-1",
                    "expected_hash": HASH_B,
                    "relation_type": "references_schema",
                }
            ],
        ),
        target,
    ]
    broken = detect_broken_links(artifacts, tenant_id="tenant-alpha")
    assert broken[0]["failure_type"] == "hash_mismatch"
    assert broken[0]["blocking"] is True


def test_35_lineage_parent_missing_detected() -> None:
    broken_item = {
        "broken_link_id": "b-lineage",
        "source_artifact_id": "child",
        "expected_target_id": "missing-parent",
        "relation_type": "derived_from",
        "failure_type": "missing_lineage_parent",
        "observed_reference": {},
        "expected_reference": {},
        "severity": "high",
        "blocking": True,
        "remediation": "restore lineage",
        "provenance": {},
    }
    schema_validator("broken-link.schema.json").validate(broken_item)


def test_36_orphan_after_tenant_filtering() -> None:
    visible = filter_visible_artifacts(
        [
            sample_node("global-a", tenant_scope="global"),
            sample_node("hidden-b", tenant_scope="tenant-beta", tenant_id="tenant-beta"),
        ],
        tenant_id="tenant-alpha",
    )
    linked = collect_linked_artifact_ids([], [])
    orphans = detect_orphan_artifacts(visible, linked)
    assert any(o["artifact_id"] == "global-a" for o in orphans)
    assert not any(o["artifact_id"] == "hidden-b" for o in orphans)


def test_37_standalone_artifact_exempt() -> None:
    archive = sample_node(
        "archive-1",
        artifact_type="source_archive",
        standalone=True,
        standalone_exemptions=["standalone_source_archive"],
    )
    assert is_standalone_exempt(archive)


def test_38_hidden_artifact_absent_from_duplicate_counts() -> None:
    visible = filter_visible_artifacts(
        [
            sample_node("a1", content_hash=HASH_A),
            sample_node(
                "a2",
                content_hash=HASH_A,
                tenant_scope="tenant-beta",
                tenant_id="tenant-beta",
            ),
        ],
        tenant_id="tenant-alpha",
    )
    dups = detect_duplicate_candidates(visible)
    assert all(len(d["artifact_ids"]) == 1 or "a2" not in d["artifact_ids"] for d in dups)


def test_39_missing_index_recommendation_generated() -> None:
    recs = detect_index_recommendations([], index_policy={"required_indexes": ["pattern_catalog"]})
    assert recs[0]["index_type"] == "pattern_catalog"


def test_40_stale_index_recommendation_generated() -> None:
    artifacts = [sample_node("stale-1", index_stale=True)]
    recs = detect_index_recommendations(artifacts)
    assert recs[0]["index_type"] == "stale_index_entry"


def test_41_no_files_modified_field() -> None:
    errors = validate_linking_output({"research_status": "complete", "files_modified": True})
    assert "forbidden_output_field:files_modified" in errors


def test_42_no_records_merged_field() -> None:
    errors = validate_linking_output({"research_status": "complete", "records_merged": True})
    assert "forbidden_output_field:records_merged" in errors


def test_43_no_records_deleted_field() -> None:
    errors = validate_linking_output({"research_status": "complete", "records_deleted": True})
    assert "forbidden_output_field:records_deleted" in errors


def test_44_no_graph_persistence_field() -> None:
    errors = validate_linking_output({"research_status": "complete", "graph_persisted": True})
    assert "forbidden_output_field:graph_persisted" in errors


def test_45_no_imported_script_execution() -> None:
    module = REPO / "app" / "knowledge" / "knowledge_linking"
    for path in module.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in FORBIDDEN_IMPORTS


def test_46_output_human_review_required() -> None:
    output = load_json_fixture("tests/fixtures/output_complete_report.json")
    assert output["human_review_required"] is True


def test_47_registry_projection_candidate(package_report) -> None:
    projection = project_validation_report(package_report)
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_48_production_eligible_false(package_report) -> None:
    view = derive_eligibility_view(project_validation_report(package_report).version_record)
    assert view.production_eligible is False


def test_49_audit_readiness_not_activation(package_report) -> None:
    audit = adapt_package_validation_report(package_report)
    assert audit.decision_readiness.value == "ready_for_audit"


def test_50_lineage_builds_in_memory(package_report) -> None:
    audit = adapt_package_validation_report(package_report)
    graph = build_package_validation_lineage(package_report, audit_report=audit)
    assert graph.nodes


def test_51_package_hash_deterministic() -> None:
    assert package_hash() == calculate_skill_package_hash(package_root())
    assert package_hash() == KB_SKILL_PACKAGE_HASHES[SKILL_ID]


def test_52_frozen_wpl_hashes_unchanged() -> None:
    manifest = load_library_manifest()
    assert manifest["library_semantic_hash"] == FROZEN_LIBRARY_SEMANTIC_HASH
    assert manifest["pilot_bundle_hash"] == FROZEN_PILOT_BUNDLE_HASH
    assert manifest["schema_bundle_hash"] == FROZEN_SCHEMA_HASH


def test_53_frozen_engineering_skill_hashes_unchanged() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        current = calculate_skill_package_hash(REPO / "packages" / "skills" / skill_id)
        assert current == KB_SKILL_PACKAGE_HASHES[skill_id]


def test_54_existing_kb_wpl_tests_remain_green() -> None:
    assert load_library_manifest()["runtime_authorized"] is False
    assert len(ALLOWED_RELATION_TYPES) >= 20
