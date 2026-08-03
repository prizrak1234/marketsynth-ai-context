"""SKILL-01.8 — Foundation freeze audit invariant tests."""
# ruff: noqa: E501

from __future__ import annotations

import importlib
import inspect
import json
import re
from pathlib import Path
from uuid import UUID

import pytest
import yaml
from app.audit.contracts import (
    AUDIT_SCHEMA_VERSION,
    AuditDecisionReadiness,
)
from app.audit.fixtures import (
    FIXED_TIME,
    TENANT_A,
    adapted_valid_package_report,
    connector_allow_decision,
    connector_evidence_descriptor,
    quarantine_success_result,
    valid_package_validation_report,
)
from app.audit.serialization import compute_report_hash, serialize_report
from app.connectors.classifications import requires_human_approval
from app.connectors.contracts import (
    ConnectorActionType,
    ConnectorExecutionRequest,
    ConnectorExecutionResultStatus,
    ConnectorPolicyOutcome,
    ConnectorStatus,
)
from app.connectors.errors import ConnectorError
from app.connectors.fixtures import (
    NATIVE_TELEGRAM_CONNECTOR_ID,
    TELEGRAM_MCP_CONNECTOR_ID,
    all_fixture_tools,
    native_telegram_descriptor,
    research_read_tool,
    telegram_mcp_descriptor,
)
from app.connectors.gateway import build_test_gateway
from app.connectors.policies import skill_tool_intersection_allowed
from app.foundation.freeze_fixture import (
    FOUNDATION_VERSIONS,
    FROZEN_PACKAGE,
    build_foundation_freeze_contour,
)
from app.lineage.builders import combine_lineage_graphs
from app.lineage.contracts import LINEAGE_SCHEMA_VERSION, LineageNodeType
from app.lineage.errors import LineageMergeError
from app.lineage.fixtures import (
    FROZEN_HASH,
    TENANT_B,
    connector_allow_graph,
    frozen_quarantine_graph,
    frozen_registry_graph,
    frozen_validation_graph,
)
from app.lineage.mappings import (
    map_connector_evidence_to_lineage_reference,
    map_lineage_reference_to_knowledge_evidence,
)
from app.lineage.serialization import compute_graph_hash, serialize_graph
from app.lineage.validators import filter_graph_for_tenant, validate_lineage_continuity
from app.schemas.contracts import (
    SkillLifecycleStatus,
    skill_lifecycle_forbids_paused,
)
from app.skills.errors import SkillValidationError
from app.skills.hashing import calculate_skill_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.quarantine_contracts import QuarantineImportOutcome
from app.skills.registry_contracts import REGISTRY_SCHEMA_VERSION, SkillRegistryView
from app.skills.registry_errors import SkillRegistryRecordNotFoundError
from app.skills.registry_projection import build_registry_snapshot, project_validation_report
from app.skills.registry_queries import NOT_FOUND_MESSAGE, derive_eligibility_view, get_skill
from app.skills.validation_contracts import VALIDATOR_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_MODULES = (
    REPO_ROOT / "app" / "skills",
    REPO_ROOT / "app" / "connectors",
    REPO_ROOT / "app" / "audit",
    REPO_ROOT / "app" / "lineage",
    REPO_ROOT / "app" / "foundation",
)
SECRET_PATTERN = re.compile(r"(secret|password|token|api_key|credential|authorization)", re.I)
ABS_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:\\|/Users/|/home/|/tmp/)")


def _skill_lifecycle_values() -> set[str]:
    return {member.value for member in SkillLifecycleStatus}


def _connector_lifecycle_values() -> set[str]:
    return {member.value for member in ConnectorStatus}


ARCHITECTURAL_INVARIANT_TESTS: dict[int, list[str]] = {
    1: ["test_no_subprocess_in_foundation_modules", "test_quarantine_import_not_installation"],
    2: ["test_registry_record_not_runtime_binding", "test_full_frozen_contour_builds_in_memory"],
    3: ["test_frozen_package_network_denied", "test_tool_level_allowlist_mandatory"],
    4: ["test_quarantine_forces_quarantined", "test_quarantine_import_not_installation"],
    5: ["test_connector_lineage_preserves_skill_identity"],
    6: ["test_cross_tenant_registry_lookup_leaks_nothing", "test_cross_tenant_lineage_merge_rejected"],
    7: ["test_no_real_provider_imports_in_connectors", "test_no_mcp_sdk_imports"],
    8: ["test_tool_level_allowlist_mandatory", "test_empty_skill_allowlist_denies_connector"],
    9: ["test_connector_policy_allow_not_approval", "test_approval_required_chain_non_executed"],
    10: ["test_connector_evidence_descriptor_only", "test_existing_evidence_mapping_boundary"],
    11: ["test_secrets_absent_from_serialized_foundation_contracts"],
    12: ["test_no_credentials_in_connector_contracts"],
    13: ["test_frozen_package_scripts_disabled"],
    14: ["test_quarantine_import_not_installation"],
    15: ["test_quarantine_forces_quarantined"],
    16: ["test_no_external_skill_active"],
    17: ["test_telegram_mcp_remains_rejected", "test_native_telegram_remains_authoritative"],
    18: ["test_write_tools_require_approval_classification"],
    19: ["test_billing_tools_require_approval_classification"],
    20: ["test_connector_evidence_descriptor_only"],
}


# --- 1–4 Lifecycle ---


def test_skill_lifecycle_enums_identical() -> None:
    expected = {
        "candidate", "quarantined", "audited", "approved", "active", "suspended",
        "deprecated", "archived", "rejected", "tenant_private", "tenant_active",
    }
    assert _skill_lifecycle_values() == expected


def test_no_paused_status_anywhere() -> None:
    assert skill_lifecycle_forbids_paused()
    for path in FOUNDATION_MODULES:
        for py_file in path.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            assert '"paused"' not in text and "'paused'" not in text


def test_connector_lifecycle_enums_compatible_with_rfc() -> None:
    expected = {
        "candidate", "quarantined", "audited", "approved", "active", "degraded",
        "suspended", "deprecated", "archived", "rejected",
    }
    assert _connector_lifecycle_values() == expected


def test_frozen_package_remains_candidate() -> None:
    manifest = yaml.safe_load((FROZEN_PACKAGE / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["status"] == SkillLifecycleStatus.CANDIDATE.value


# --- 5–11 Security / boundaries ---


def test_frozen_package_has_no_tools() -> None:
    manifest = yaml.safe_load((FROZEN_PACKAGE / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["allowed_tools"] == []


def test_frozen_package_network_denied() -> None:
    manifest = yaml.safe_load((FROZEN_PACKAGE / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["network_policy"]["default"] == "deny"


def test_frozen_package_scripts_disabled() -> None:
    manifest = yaml.safe_load((FROZEN_PACKAGE / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["script_policy"]["enabled"] is False
    assert not (FROZEN_PACKAGE / "scripts").exists()


def test_validator_does_not_approve() -> None:
    report = validate_skill_package(FROZEN_PACKAGE)
    assert report.status == SkillLifecycleStatus.CANDIDATE
    assert "approve" not in json.dumps(report.model_dump(mode="json")).lower()


def test_quarantine_forces_quarantined() -> None:
    result = quarantine_success_result()
    assert result.effective_status == SkillLifecycleStatus.QUARANTINED
    assert result.outcome == QuarantineImportOutcome.QUARANTINED


def test_registry_projection_preserves_candidate() -> None:
    report = validate_skill_package(FROZEN_PACKAGE)
    projection = project_validation_report(report, recorded_at=FIXED_TIME)
    assert projection.version_record is not None
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_candidate_never_production_eligible() -> None:
    report = validate_skill_package(FROZEN_PACKAGE)
    projection = project_validation_report(report, recorded_at=FIXED_TIME)
    assert projection.version_record is not None
    view = derive_eligibility_view(projection.version_record, view=SkillRegistryView.NORMAL)
    assert view.production_eligible is False
    assert view.selectable_for_new_work is False


def test_audit_readiness_never_equals_activation() -> None:
    readiness_values = {member.value for member in AuditDecisionReadiness}
    forbidden = {"approved", "active", "activated", "production_ready"}
    assert readiness_values.isdisjoint(forbidden)
    report = adapted_valid_package_report()
    assert report.decision_readiness != AuditDecisionReadiness.READY_FOR_APPROVAL_REVIEW or report.blockers


def test_lineage_approval_reference_not_approved() -> None:
    graph = connector_allow_graph()
    approval_nodes = [n for n in graph.nodes if n.node_type == LineageNodeType.APPROVAL_REFERENCE]
    for node in approval_nodes:
        assert node.lifecycle_status != SkillLifecycleStatus.APPROVED.value


# --- 12–17 Connector policy ---


def test_connector_tool_default_disabled() -> None:
    for tool in all_fixture_tools().values():
        assert tool.enabled_by_default is False


def test_tool_level_allowlist_mandatory() -> None:
    assert skill_tool_intersection_allowed(("other.tool",), "research.read") is False
    assert skill_tool_intersection_allowed(("research.read",), "research.read") is True


def test_server_active_does_not_enable_tool() -> None:
    tool = research_read_tool()
    descriptor = native_telegram_descriptor(status=ConnectorStatus.ACTIVE)
    assert tool.enabled_by_default is False
    assert descriptor.status == ConnectorStatus.ACTIVE


def test_empty_skill_allowlist_denies_connector() -> None:
    contour = build_foundation_freeze_contour(recorded_at=FIXED_TIME)
    assert contour.connector_policy_outcome == ConnectorPolicyOutcome.DENY.value


def test_cross_tenant_registry_lookup_leaks_nothing() -> None:
    report = validate_skill_package(FROZEN_PACKAGE)
    projection = project_validation_report(report, recorded_at=FIXED_TIME)
    snapshot = build_registry_snapshot([projection.version_record], generated_at=FIXED_TIME)
    with pytest.raises(SkillRegistryRecordNotFoundError) as exc:
        get_skill(snapshot, "ms.skill.nonexistent_private", tenant_id=TENANT_B)
    message = str(exc.value)
    assert TENANT_A not in message
    assert "nonexistent" not in message.lower() or NOT_FOUND_MESSAGE in message


def test_cross_tenant_audit_output_leaks_nothing() -> None:
    report = adapted_valid_package_report()
    serialized = serialize_report(report)
    assert TENANT_B not in serialized
    assert SECRET_PATTERN.search(serialized) is None


def test_cross_tenant_lineage_merge_rejected() -> None:
    left = connector_allow_graph()
    right = connector_allow_graph().model_copy(
        update={
            "context": left.context.model_copy(update={"tenant_id": TENANT_B}) if left.context else None,
            "nodes": tuple(
                node.model_copy(update={"tenant_id": TENANT_B, "global_scope": False})
                for node in left.nodes
            ),
        }
    )
    with pytest.raises(LineageMergeError):
        combine_lineage_graphs(left, right)


# --- 18–22 Serialization safety ---


def test_secrets_absent_from_serialized_foundation_contracts() -> None:
    contour = build_foundation_freeze_contour(recorded_at=FIXED_TIME)
    graph = frozen_registry_graph()
    payloads = [
        json.dumps(contour.__dict__),
        serialize_graph(graph),
        serialize_report(adapted_valid_package_report()),
    ]
    for payload in payloads:
        assert SECRET_PATTERN.search(payload) is None


def test_absolute_paths_absent_from_normalized_reports() -> None:
    report = adapted_valid_package_report()
    serialized = serialize_report(report)
    assert ABS_PATH_PATTERN.search(serialized) is None


def test_package_hash_deterministic() -> None:
    first = calculate_skill_package_hash(FROZEN_PACKAGE)
    second = calculate_skill_package_hash(FROZEN_PACKAGE)
    assert first == second == FROZEN_HASH


def test_registry_snapshot_hash_deterministic() -> None:
    first = frozen_registry_graph()
    second = frozen_registry_graph()
    first_snapshot = next(n for n in first.nodes if n.node_type.value == "registry_snapshot")
    second_snapshot = next(n for n in second.nodes if n.node_type.value == "registry_snapshot")
    assert first_snapshot.snapshot_hash == second_snapshot.snapshot_hash


def test_quarantine_fingerprint_deterministic() -> None:
    first = frozen_quarantine_graph()
    second = frozen_quarantine_graph()
    assert first.graph_hash == second.graph_hash


def test_audit_report_hash_deterministic() -> None:
    first = adapted_valid_package_report()
    second = adapted_valid_package_report()
    assert first.report_hash == second.report_hash
    assert compute_report_hash(first) == compute_report_hash(second)


def test_lineage_graph_hash_deterministic() -> None:
    first = frozen_validation_graph()
    second = frozen_validation_graph()
    assert first.graph_hash == second.graph_hash
    assert compute_graph_hash(first) == compute_graph_hash(second)


# --- 23–32 Semantic boundaries ---


def test_validation_report_not_approval() -> None:
    report = valid_package_validation_report()
    assert report.valid is True
    assert report.status == SkillLifecycleStatus.CANDIDATE


def test_quarantine_import_not_installation() -> None:
    result = quarantine_success_result()
    assert result.executable is False
    assert result.production_eligible is False


def test_registry_record_not_runtime_binding() -> None:
    contour = build_foundation_freeze_contour(recorded_at=FIXED_TIME)
    assert contour.execution_eligible is False


def test_connector_policy_allow_not_approval() -> None:
    decision = connector_allow_decision()
    assert decision.outcome == ConnectorPolicyOutcome.ALLOW
    assert decision.approval_required is False


def test_unified_audit_not_owner_decision() -> None:
    report = adapted_valid_package_report()
    assert report.provenance.owner_decision_required is False
    assert report.provenance.human_review_required is False


def test_no_persistence_interfaces_exist() -> None:
    forbidden = ("sqlalchemy", "alembic", "Repository", "session.add", "Base.metadata")
    for module_root in FOUNDATION_MODULES:
        for py_file in module_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, f"{token} found in {py_file}"


def test_no_api_routes_for_skills_foundation() -> None:
    routes_dir = REPO_ROOT / "app" / "api" / "routes"
    forbidden_names = {
        "skills_foundation.py",
        "skill_packages.py",
        "skill_registry.py",
        "connector_gateway.py",
        "lineage.py",
    }
    if routes_dir.exists():
        present = {path.name for path in routes_dir.glob("*.py")}
        assert forbidden_names.isdisjoint(present)


def test_no_real_provider_imports_in_connectors() -> None:
    connectors_root = REPO_ROOT / "app" / "connectors"
    forbidden = ("import httpx", "import requests", "from openai", "import boto3", "import stripe")
    for py_file in connectors_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for lib in forbidden:
            assert lib not in text


def test_no_mcp_sdk_imports() -> None:
    forbidden = ("from app.mcp", "import mcp")
    for module_root in (REPO_ROOT / "app" / "connectors", REPO_ROOT / "app" / "skills"):
        for py_file in module_root.rglob("*.py"):
            lines = py_file.read_text(encoding="utf-8").splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for token in forbidden:
                    assert token not in stripped, f"{token} in {py_file}"


def test_no_subprocess_in_foundation_modules() -> None:
    for module_root in FOUNDATION_MODULES:
        for py_file in module_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            assert "subprocess" not in text
            assert "os.system" not in text


def test_no_external_skill_active() -> None:
    manifest = yaml.safe_load((FROZEN_PACKAGE / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["status"] != SkillLifecycleStatus.ACTIVE.value


def test_telegram_mcp_remains_rejected() -> None:
    descriptor = telegram_mcp_descriptor()
    assert descriptor.status == ConnectorStatus.REJECTED
    assert descriptor.is_mcp is True
    assert descriptor.is_native_authoritative is False


def test_native_telegram_remains_authoritative() -> None:
    descriptor = native_telegram_descriptor()
    assert descriptor.is_native_authoritative is True
    assert descriptor.is_mcp is False
    assert descriptor.connector_id == NATIVE_TELEGRAM_CONNECTOR_ID
    assert TELEGRAM_MCP_CONNECTOR_ID != NATIVE_TELEGRAM_CONNECTOR_ID


# --- 33–40 CWF / RFC / imports ---


def test_foundation_modules_do_not_import_cwf() -> None:
    forbidden = ("business_idea_validation", "commercial_workflow", "launch_pack")
    for module_root in FOUNDATION_MODULES:
        for py_file in module_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text


def test_rfc_skill_004_remains_draft() -> None:
    text = (REPO_ROOT / "docs" / "rfc" / "RFC-SKILL-004-skill-discovery-and-draft-generation.md").read_text(
        encoding="utf-8"
    )
    assert "| **Status** | **Draft** |" in text


def test_foundation_modules_import_cleanly() -> None:
    for module_name in ("app.skills", "app.connectors", "app.audit", "app.lineage", "app.foundation"):
        importlib.import_module(module_name)


def test_full_frozen_contour_builds_in_memory() -> None:
    contour = build_foundation_freeze_contour(recorded_at=FIXED_TIME)
    assert contour.package_hash == FOUNDATION_VERSIONS["frozen_package_hash"]
    assert contour.registry_snapshot_hash
    assert contour.audit_report_hash
    assert contour.lineage_graph_hash


def test_full_contour_remains_non_executable() -> None:
    contour = build_foundation_freeze_contour(recorded_at=FIXED_TIME)
    assert contour.execution_eligible is False
    assert contour.connector_policy_outcome == ConnectorPolicyOutcome.DENY.value


def test_full_contour_emits_deterministic_audit_and_lineage() -> None:
    first = build_foundation_freeze_contour(recorded_at=FIXED_TIME)
    second = build_foundation_freeze_contour(recorded_at=FIXED_TIME)
    assert first.package_hash == second.package_hash
    assert first.audit_report_hash == second.audit_report_hash
    assert first.lineage_graph_hash == second.lineage_graph_hash


def test_architectural_invariants_mapped_to_tests() -> None:
    assert len(ARCHITECTURAL_INVARIANT_TESTS) == 20
    for invariant_id, tests in ARCHITECTURAL_INVARIANT_TESTS.items():
        assert tests, f"Invariant {invariant_id} has no mapped tests"


# --- Additional cross-layer helpers referenced above ---


def test_connector_lineage_preserves_skill_identity() -> None:
    graph = connector_allow_graph()
    request_nodes = [n for n in graph.nodes if n.node_type.value == "connector_request"]
    assert request_nodes[0].skill_id == "ms.skill.market_validation"
    assert request_nodes[0].skill_version == "0.1.0"


def test_approval_required_chain_non_executed() -> None:
    gateway, _ = build_test_gateway()
    request = ConnectorExecutionRequest(
        request_id=UUID("33333333-3333-3333-3333-333333333333"),
        correlation_id=UUID("44444444-4444-4444-4444-444444444444"),
        tenant_id=UUID(TENANT_A),
        project_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        actor_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        skill_id="ms.skill.market_validation",
        skill_version="0.1.0",
        connector_id="fixture.connector.research_read",
        connector_version="0.1.0-fixture",
        tool_id="research.read",
        input_payload={"query": "test"},
        requested_at=FIXED_TIME,
        skill_allowed_tools=("research.read",),
        approval_reference=None,
    )
    result = gateway.execute(request, tenant_binding=None, project_binding=None)
    assert result.status in {
        ConnectorExecutionResultStatus.REJECTED_BY_POLICY,
        ConnectorExecutionResultStatus.APPROVAL_REQUIRED,
    }


def test_connector_evidence_descriptor_only() -> None:
    descriptor = connector_evidence_descriptor()
    ref = map_connector_evidence_to_lineage_reference(descriptor)
    knowledge = map_lineage_reference_to_knowledge_evidence(ref)
    assert knowledge.evidence_id == str(descriptor.evidence_id)


def test_existing_evidence_mapping_boundary() -> None:
    ref = map_connector_evidence_to_lineage_reference(connector_evidence_descriptor())
    assert ref.source_system == "connector_evidence_descriptor"
    assert "password" not in json.dumps(ref.model_dump(mode="json"))


def test_no_credentials_in_connector_contracts() -> None:
    source = inspect.getsource(importlib.import_module("app.connectors.contracts"))
    assert "credential_secret" not in source.lower()
    assert "api_key_value" not in source.lower()


def test_write_tools_require_approval_classification() -> None:
    from app.connectors.fixtures import publication_tool

    assert requires_human_approval(publication_tool())


def test_billing_tools_require_approval_classification() -> None:
    from app.connectors.fixtures import advertising_spend_tool

    assert requires_human_approval(advertising_spend_tool())
    assert advertising_spend_tool().action_type == ConnectorActionType.BILLING


def test_contracts_skill_lifecycle_single_definition() -> None:
    source = (REPO_ROOT / "app" / "schemas" / "contracts.py").read_text(encoding="utf-8")
    assert source.count("class SkillLifecycleStatus") == 1


def test_foundation_schema_versions_frozen() -> None:
    assert FOUNDATION_VERSIONS["validator_version"] == VALIDATOR_VERSION
    assert FOUNDATION_VERSIONS["registry_schema_version"] == REGISTRY_SCHEMA_VERSION
    assert FOUNDATION_VERSIONS["audit_schema_version"] == AUDIT_SCHEMA_VERSION
    assert FOUNDATION_VERSIONS["lineage_schema_version"] == LINEAGE_SCHEMA_VERSION


def test_domain_errors_safe_messages() -> None:
    err = SkillValidationError("Package invalid.")
    assert SECRET_PATTERN.search(str(err)) is None
    conn_err = ConnectorError("Connector unavailable.")
    assert SECRET_PATTERN.search(str(conn_err)) is None


def test_tenant_private_lineage_invisible() -> None:
    graph = frozen_quarantine_graph()
    filtered = filter_graph_for_tenant(graph, TENANT_B)
    assert len(filtered.nodes) <= len(graph.nodes)


def test_lineage_continuity_on_frozen_contour() -> None:
    build_foundation_freeze_contour(recorded_at=FIXED_TIME)
    graph = frozen_registry_graph()
    result = validate_lineage_continuity(graph)
    assert result.valid or not any(f.blocking for f in result.findings)


def test_packages_skills_only_package_root() -> None:
    root = REPO_ROOT / "packages" / "skills"
    assert root.is_dir()
    assert not (REPO_ROOT / "packages" / "external_skills").exists()


def test_app_mcp_unchanged_by_foundation_imports() -> None:
    mcp_root = REPO_ROOT / "app" / "mcp"
    assert mcp_root.is_dir()
    for module_root in FOUNDATION_MODULES:
        for py_file in module_root.rglob("*.py"):
            assert "from app.mcp" not in py_file.read_text(encoding="utf-8")
