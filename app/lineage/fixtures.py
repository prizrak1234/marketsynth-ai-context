"""Synthetic lineage fixtures for tests (SKILL-01.7)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from app.audit.fixtures import (
    FIXED_TIME,
    TENANT_A,
    adapted_connector_allow,
    adapted_quarantine_success,
    adapted_valid_package_report,
    connector_allow_decision,
    connector_deny_decision,
    connector_evidence_descriptor,
    connector_require_approval_decision,
    quarantine_success_result,
    valid_package_validation_report,
)
from app.connectors.contracts import (
    ConnectorExecutionRequest,
    ConnectorExecutionResult,
    ConnectorExecutionResultStatus,
)
from app.lineage.builders import (
    build_audit_lineage,
    build_connector_request_lineage,
    build_connector_result_lineage,
    build_package_validation_lineage,
    build_quarantine_lineage,
    build_registry_projection_lineage,
)
from app.schemas.contracts import SkillLifecycleStatus
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import build_registry_snapshot, project_validation_report
from app.skills.validation_contracts import SkillPackageValidationReport

FROZEN_PACKAGE = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.market_validation"
)

FROZEN_HASH = "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133"
TENANT_B = "22222222-2222-2222-2222-222222222222"
PROJECT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ACTOR = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_FROZEN_DISK_REPORT: SkillPackageValidationReport | None = None


def _frozen_disk_validation_report() -> SkillPackageValidationReport:
    """Cached disk validation — stable within process for deterministic lineage fixtures."""
    global _FROZEN_DISK_REPORT
    if _FROZEN_DISK_REPORT is None:
        _FROZEN_DISK_REPORT = validate_skill_package(FROZEN_PACKAGE)
    return _FROZEN_DISK_REPORT


def frozen_validation_graph():
    report = valid_package_validation_report()
    audit = adapted_valid_package_report()
    return build_package_validation_lineage(report, audit_report=audit)


def frozen_quarantine_graph():
    return build_quarantine_lineage(
        quarantine_success_result(),
        audit_report=adapted_quarantine_success(),
    )


def frozen_registry_graph():
    report = _frozen_disk_validation_report()
    projection = project_validation_report(report, recorded_at=FIXED_TIME)
    validation_graph = build_package_validation_lineage(
        report,
        audit_report=adapted_valid_package_report(),
    )
    assert projection.version_record is not None
    snapshot = build_registry_snapshot(
        [projection.version_record],
        generated_at=FIXED_TIME,
        snapshot_id="snapshot-frozen-market-validation",
    )
    return build_registry_projection_lineage(
        projection,
        snapshot=snapshot,
        validation_graph=validation_graph,
    )


def connector_request():
    return ConnectorExecutionRequest(
        request_id=uuid4(),
        correlation_id=uuid4(),
        tenant_id=UUID(TENANT_A),
        project_id=PROJECT_A,
        actor_id=ACTOR,
        skill_id="ms.skill.market_validation",
        skill_version="0.1.0",
        connector_id="fixture.connector.research_read",
        connector_version="0.1.0-fixture",
        tool_id="research.read",
        input_payload={"query": "marketsynth"},
        requested_at=FIXED_TIME,
        skill_allowed_tools=("research.read",),
    )


def connector_allow_graph():
    return build_connector_request_lineage(
        connector_request(),
        connector_allow_decision(),
        audit_report=adapted_connector_allow(),
    )


def connector_deny_graph():
    return build_connector_request_lineage(
        connector_request(),
        connector_deny_decision(),
    )


def connector_approval_graph():
    return build_connector_request_lineage(
        connector_request(),
        connector_require_approval_decision(),
    )


def connector_result_graph():
    request = connector_request()
    result = ConnectorExecutionResult(
        request_id=request.request_id,
        connector_id=request.connector_id,
        connector_version=request.connector_version,
        tool_id=request.tool_id,
        status=ConnectorExecutionResultStatus.SUCCEEDED,
        output_payload={"synthetic": True},
        safe_provider_metadata={"provider": "synthetic"},
        started_at=FIXED_TIME,
        finished_at=FIXED_TIME,
        duration_ms=0,
        skill_id=request.skill_id,
        skill_version=request.skill_version,
        evidence_descriptor=connector_evidence_descriptor(),
    )
    return build_connector_result_lineage(
        request,
        result,
        policy=connector_allow_decision(),
    )


def audit_aggregation_graph():
    return build_audit_lineage(adapted_valid_package_report())


def archived_version_node_payload():
    return {
        "skill_id": "ms.skill.market_validation",
        "skill_version": "0.0.9",
        "package_hash": "archivedhash" + "0" * 54,
        "lifecycle_status": SkillLifecycleStatus.ARCHIVED.value,
    }


def deprecated_version_node_payload():
    return {
        "skill_id": "ms.skill.market_validation",
        "skill_version": "0.0.8",
        "package_hash": "deprecatedhash" + "0" * 52,
        "lifecycle_status": SkillLifecycleStatus.DEPRECATED.value,
    }
