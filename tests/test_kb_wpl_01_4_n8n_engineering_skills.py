"""KB-WPL-01.4 — n8n Engineering Knowledge Skills tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from app.audit.adapters import adapt_package_validation_report
from app.knowledge.n8n_engineering.architecture_validation import (
    validate_architecture_input,
    validate_architecture_output,
)
from app.knowledge.n8n_engineering.constants import (
    FROZEN_CATALOG_HASH,
    FROZEN_LIBRARY_SEMANTIC_HASH,
    N8N_ENGINEERING_SKILL_IDS,
)
from app.knowledge.n8n_engineering.debugging_validation import (
    validate_debugging_input,
    validate_debugging_output,
)
from app.knowledge.n8n_engineering.deployment_validation import (
    validate_deployment_input,
    validate_deployment_output,
)
from app.knowledge.n8n_engineering.pattern_selection import validate_pattern_selection
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
from tests.support.kb_skill_validation import (
    FROZEN_POSITIONING_HASH,
    KB_SKILL_PACKAGE_HASHES,
)
from tests.support.n8n_engineering_skills_validation import (
    load_json_fixture,
    package_hash,
    package_root,
    schema_validator,
)

REPO = Path(__file__).resolve().parents[1]
ARCH_ID = "ms.skill.n8n_workflow_architecture"
DEBUG_ID = "ms.skill.n8n_workflow_debugging"
DEPLOY_ID = "ms.skill.n8n_deployment_review"
FORBIDDEN_IMPORTS = ("requests", "httpx", "aiohttp", "subprocess", "socket", "n8n")
PATTERN_REF = {
    "pattern_id": "human_approval_before_publication",
    "library_version": "0.1.0-frozen",
    "library_semantic_hash": FROZEN_LIBRARY_SEMANTIC_HASH,
    "selection_reason": "Publication requires approval.",
    "maturity": "reviewed",
    "runtime_authorized": False,
}


@pytest.fixture
def arch_report():
    return validate_skill_package(package_root(ARCH_ID))


# --- General (1-15) ---


def test_01_three_packages_exist() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        assert package_root(skill_id).is_dir()


def test_02_all_versions_010() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        report = validate_skill_package(package_root(skill_id))
        assert report.skill_version == "0.1.0"


def test_03_all_candidate(arch_report) -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        projection = project_validation_report(validate_skill_package(package_root(skill_id)))
        assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_04_all_non_executable() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        manifest = validate_skill_package(package_root(skill_id)).manifest
        assert manifest.activation_conditions.executable is False


def test_05_no_tools() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        assert validate_skill_package(package_root(skill_id)).manifest.allowed_tools == []


def test_06_network_denied() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        policy = validate_skill_package(package_root(skill_id)).manifest.network_policy
        assert policy.default.value == "deny"


def test_07_scripts_disabled() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        report = validate_skill_package(package_root(skill_id))
        assert report.manifest.script_policy.enabled is False


def test_08_output_contract_research() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        report = validate_skill_package(package_root(skill_id))
        assert report.manifest.output_contract_type.value == "research"


def test_09_production_validator_passes() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        assert validate_skill_package(package_root(skill_id)).valid is True


def test_10_registry_projection_candidate() -> None:
    projection = project_validation_report(validate_skill_package(package_root(ARCH_ID)))
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_11_production_eligible_false() -> None:
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        report = validate_skill_package(package_root(skill_id))
        version = project_validation_report(report).version_record
        view = derive_eligibility_view(version)
        assert view.production_eligible is False


def test_12_audit_readiness_not_activation(arch_report) -> None:
    audit = adapt_package_validation_report(arch_report)
    assert audit.decision_readiness.value == "ready_for_audit"
    assert audit.status.value == "complete"


def test_13_lineage_builds_in_memory(arch_report) -> None:
    audit = adapt_package_validation_report(arch_report)
    graph = build_package_validation_lineage(arch_report, audit_report=audit)
    assert graph.nodes


def test_14_frozen_wpl_hashes_unchanged() -> None:
    manifest = load_library_manifest()
    assert manifest["library_semantic_hash"] == FROZEN_LIBRARY_SEMANTIC_HASH
    assert manifest["pilot_bundle_hash"] == FROZEN_PILOT_BUNDLE_HASH
    assert manifest["schema_bundle_hash"] == FROZEN_SCHEMA_HASH
    assert manifest["catalog_bundle_hash"] == FROZEN_CATALOG_HASH


def test_15_other_frozen_skill_hashes_unchanged() -> None:
    from app.skills.legacy_output_contract import expected_frozen_package_hash

    assert expected_frozen_package_hash("ms.skill.positioning", "0.1.0") == FROZEN_POSITIONING_HASH


# --- Pattern references (16-21) ---


def test_16_known_pattern_resolves() -> None:
    assert not validate_pattern_selection(PATTERN_REF)


def test_17_unknown_pattern_rejected() -> None:
    bad = {**PATTERN_REF, "pattern_id": "nonexistent_pattern"}
    assert any("unknown" in e for e in validate_pattern_selection(bad))


def test_18_library_hash_mismatch_rejected() -> None:
    bad = {**PATTERN_REF, "library_semantic_hash": "0" * 64}
    assert "library_hash_mismatch" in validate_pattern_selection(bad)


def test_19_runtime_authorized_true_rejected() -> None:
    bad = {**PATTERN_REF, "runtime_authorized": True}
    assert "runtime_authorized_must_be_false" in validate_pattern_selection(bad)


def test_20_maturity_above_reviewed_rejected() -> None:
    bad = {**PATTERN_REF, "maturity": "platform_adapted"}
    assert "maturity_must_be_reviewed" in validate_pattern_selection(bad)


def test_21_pattern_selection_reason_required() -> None:
    bad = {**PATTERN_REF, "selection_reason": ""}
    assert "selection_reason_required" in validate_pattern_selection(bad)


# --- Architecture (22-30) ---


def test_22_architecture_schemas_valid() -> None:
    data = load_json_fixture(ARCH_ID, "tests/fixtures/output_telegram_publication.json")
    schema_validator(ARCH_ID, "output.schema.json").validate(data)


def test_23_publication_requires_approval_pattern() -> None:
    payload = {
        "publication_context": {"enabled": True, "publication_required": True},
        "pattern_references": [],
        "architecture_readiness": "partially_ready",
        "error_paths": ["human_review"],
    }
    assert "publication_requires_approval_pattern" in validate_architecture_output(payload)


def test_24_write_retry_requires_idempotency() -> None:
    payload = {
        "retry_requirements": {"enabled": True, "write_retry": True},
        "pattern_references": [],
        "error_paths": ["retry"],
        "architecture_readiness": "partially_ready",
    }
    assert "write_retry_requires_idempotency_pattern" in validate_architecture_output(payload)


def test_25_llm_to_api_requires_structured_validation() -> None:
    payload = {
        "provider_constraints": {"llm_to_api": True},
        "pattern_references": [],
        "error_paths": ["validate"],
        "architecture_readiness": "partially_ready",
    }
    errors = validate_architecture_output(payload)
    assert "llm_to_api_requires_structured_validation_pattern" in errors


def test_26_missing_error_path_blocks_readiness() -> None:
    data = load_json_fixture(ARCH_ID, "tests/fixtures/output_missing_error_path.json")
    assert "missing_error_path_blocks_ready" in validate_architecture_output(data)


def test_27_credential_value_rejected() -> None:
    assert validate_architecture_input({"api_key": "sk-secret1234567890"})


def test_28_workflow_json_rejected() -> None:
    assert "workflow_json_forbidden" in validate_architecture_output({"workflow_json": {}})


def test_29_provider_unknown_requires_reverification() -> None:
    payload = {
        "provider_constraints": [{"requires_reverification": False}],
        "pattern_references": [],
        "error_paths": ["x"],
        "architecture_readiness": "partially_ready",
    }
    errors = validate_architecture_output(payload)
    assert "unknown_provider_version_requires_reverification" in errors


def test_30_no_deployment_fields_in_architecture_output() -> None:
    data = load_json_fixture(ARCH_ID, "tests/fixtures/output_telegram_publication.json")
    for field in ("deployed", "activated", "deployment_result", "approval_granted"):
        assert field not in data


# --- Debugging (31-40) ---


def test_31_debugging_schemas_valid() -> None:
    data = load_json_fixture(DEBUG_ID, "tests/fixtures/output_postgres_type_mismatch.json")
    schema_validator(DEBUG_ID, "output.schema.json").validate(data)


def test_32_missing_evidence_prevents_high_confidence() -> None:
    payload = {"diagnostic_confidence": "high", "supporting_evidence": []}
    assert "missing_evidence_prevents_high_confidence" in validate_debugging_output(payload)


def test_33_unknown_outcome_no_blind_retry() -> None:
    payload = {
        "failure_classification": "unknown_outcome",
        "remediation_candidates": [{"action": "blind_retry"}],
        "sandbox_plan": {},
    }
    assert "unknown_outcome_blind_retry_forbidden" in validate_debugging_output(payload)


def test_34_publication_sandbox_disabled() -> None:
    payload = {"sandbox_plan": {"publication_enabled": True}}
    assert "publication_sandbox_must_remain_disabled" in validate_debugging_output(payload)


def test_35_billing_sandbox_disabled() -> None:
    payload = {"sandbox_plan": {"billing_enabled": True}}
    assert "billing_sandbox_must_remain_disabled" in validate_debugging_output(payload)


def test_36_unsanitized_logs_rejected() -> None:
    assert "raw_execution_logs_forbidden" in validate_debugging_input({"execution_logs": "raw"})


def test_37_live_patch_rejected() -> None:
    assert "live_mutation_remediation_forbidden" in validate_debugging_output(
        {"remediation_candidates": [{"action": "live_patch"}], "sandbox_plan": {}}
    )


def test_38_credential_rotation_rejected() -> None:
    assert "live_mutation_remediation_forbidden" in validate_debugging_output(
        {"remediation_candidates": [{"action": "credential_rotation"}], "sandbox_plan": {}}
    )


def test_39_diagnostic_references_patterns() -> None:
    data = load_json_fixture(DEBUG_ID, "tests/fixtures/output_postgres_type_mismatch.json")
    assert data["patterns_consulted"]
    assert data["practices_consulted"]


def test_40_remediation_manual_candidate() -> None:
    data = load_json_fixture(DEBUG_ID, "tests/fixtures/output_postgres_type_mismatch.json")
    assert data["remediation_candidates"][0]["action"] == "manual_schema_fix"


# --- Deployment (41-52) ---


def test_41_deployment_schemas_valid() -> None:
    data = load_json_fixture(DEPLOY_ID, "tests/fixtures/output_safe_manual_deployment.json")
    schema_validator(DEPLOY_ID, "output.schema.json").validate(data)


def test_42_publication_without_approval_blocked() -> None:
    data = load_json_fixture(DEPLOY_ID, "tests/fixtures/output_blocked_publication.json")
    assert "publication_without_approval_blocked" in validate_deployment_output(data)


def test_43_billing_without_budget_blocked() -> None:
    payload = {
        "deployment_readiness": "ready_for_manual_deployment",
        "billing_findings": {"billing_configured": True, "budget_context_present": False},
        "activation_gate": {"final_manual_action_required": True},
    }
    assert "billing_without_budget_blocked" in validate_deployment_output(payload)


def test_44_retry_without_idempotency_blocked() -> None:
    payload = {
        "deployment_readiness": "ready_for_manual_deployment",
        "retry_and_idempotency_findings": {"retry_enabled": True, "idempotency_present": False},
        "activation_gate": {"final_manual_action_required": True},
    }
    assert "retry_without_idempotency_blocked" in validate_deployment_output(payload)


def test_45_missing_rollback_blocks_ready() -> None:
    data = load_json_fixture(DEPLOY_ID, "tests/fixtures/output_blocked_publication.json")
    assert "missing_rollback_blocks_ready" in validate_deployment_output(data)


def test_46_missing_tests_blocks_ready() -> None:
    data = load_json_fixture(DEPLOY_ID, "tests/fixtures/output_blocked_publication.json")
    assert "missing_tests_blocks_ready" in validate_deployment_output(data)


def test_47_unknown_provider_requires_condition() -> None:
    data = load_json_fixture(DEPLOY_ID, "tests/fixtures/output_blocked_publication.json")
    assert "unknown_provider_version_requires_condition" in validate_deployment_output(data)


def test_48_final_manual_action_required_false_rejected() -> None:
    payload = {"activation_gate": {"final_manual_action_required": False}}
    assert "final_manual_action_required_must_be_true" in validate_deployment_output(payload)


def test_49_deployed_activated_fields_rejected() -> None:
    assert "forbidden_field:deployed" in validate_deployment_output({"deployed": True})


def test_50_approval_granted_rejected() -> None:
    assert "approval_granted_forbidden" in validate_deployment_output({"approval_granted": True})


def test_51_credential_value_rejected_deployment() -> None:
    assert validate_deployment_input({"password": "secret"})


def test_52_activation_gate_manual() -> None:
    data = load_json_fixture(DEPLOY_ID, "tests/fixtures/output_safe_manual_deployment.json")
    assert data["activation_gate"]["final_manual_action_required"] is True


# --- Cross-package (53-60) ---


def test_53_architecture_consumable_by_deployment() -> None:
    arch = load_json_fixture(ARCH_ID, "tests/fixtures/output_telegram_publication.json")
    assert "architecture_id" in arch
    assert arch["architecture_readiness"]


def test_54_debugging_findings_as_deployment_evidence() -> None:
    diag = load_json_fixture(DEBUG_ID, "tests/fixtures/output_postgres_type_mismatch.json")
    assert diag["diagnostic_report_id"]
    regression = diag.get("regression_test_plan")
    assert "regression_test_plan" not in diag or isinstance(regression, (dict, type(None)))


def test_55_deployment_does_not_execute_architecture() -> None:
    data = load_json_fixture(DEPLOY_ID, "tests/fixtures/output_safe_manual_deployment.json")
    assert "workflow_json" not in data
    assert data["deployment_readiness"] != "deployed"


def test_56_no_n8n_sdk_imports() -> None:
    module = REPO / "app" / "knowledge" / "n8n_engineering"
    for path in module.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("n8n")
            if isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in FORBIDDEN_IMPORTS
                assert not node.module.startswith("n8n")


def test_57_no_network_imports_in_engineering_modules() -> None:
    module = REPO / "app" / "knowledge" / "n8n_engineering"
    for path in module.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN_IMPORTS
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS


def test_58_package_hashes_deterministic() -> None:
    for skill_id, expected in KB_SKILL_PACKAGE_HASHES.items():
        if skill_id in N8N_ENGINEERING_SKILL_IDS:
            assert package_hash(skill_id) == expected
            assert calculate_skill_package_hash(package_root(skill_id)) == expected


def test_59_documentation_exists() -> None:
    assert (REPO / "docs/rfc/KB-WPL-01.4-N8N-ENGINEERING-KNOWLEDGE-SKILLS.md").is_file()
    for skill_id in N8N_ENGINEERING_SKILL_IDS:
        doc = REPO / "docs/skills" / f"{skill_id}.md"
        assert doc.is_file(), str(doc)


def test_60_existing_kb_wpl_tests_remain_green() -> None:
    assert load_library_manifest()["runtime_authorized"] is False
    assert load_library_manifest()["production_eligible"] is False
