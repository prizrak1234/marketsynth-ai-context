"""Integrated in-memory Foundation freeze contour (SKILL-01.8).

Builds the full package → validation → quarantine → registry → connector → audit → lineage
chain without persistence or runtime execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.audit.adapters import (
    adapt_connector_policy_decision,
    adapt_package_validation_report,
    adapt_quarantine_import_result,
)
from app.audit.aggregator import aggregate_audit_reports
from app.audit.contracts import AuditTargetReference, AuditTargetType
from app.audit.fixtures import FIXED_TIME, TENANT_A, connector_policy_target
from app.connectors.contracts import ConnectorExecutionRequest
from app.connectors.fixtures import CONNECTOR_VERSION, RESEARCH_CONNECTOR_ID, RESEARCH_TOOL_ID
from app.connectors.gateway import build_test_gateway
from app.lineage.builders import (
    build_audit_lineage,
    build_connector_request_lineage,
    build_package_validation_lineage,
    build_quarantine_lineage,
    build_registry_projection_lineage,
    combine_lineage_graphs,
)
from app.schemas.contracts import SkillLifecycleStatus
from app.skills.hashing import calculate_skill_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.quarantine_contracts import QuarantineImportRequest, QuarantineSourceType
from app.skills.quarantine_import import import_skill_package_to_quarantine
from app.skills.registry_contracts import SkillRegistryView
from app.skills.registry_projection import build_registry_snapshot, project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from app.skills.validation_contracts import VALIDATOR_VERSION

FROZEN_PACKAGE = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "skills"
    / "ms.skill.market_validation"
)
QUARANTINE_EXTERNAL = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "skills"
    / "quarantine"
    / "valid_external"
)
PROJECT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ACTOR_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_CACHED_VALIDATION_REPORT = None
_CACHED_QUARANTINE_RESULT = None


def _cached_validation_report():
    global _CACHED_VALIDATION_REPORT
    if _CACHED_VALIDATION_REPORT is None:
        _CACHED_VALIDATION_REPORT = validate_skill_package(FROZEN_PACKAGE)
    return _CACHED_VALIDATION_REPORT


def _cached_quarantine_result(*, timestamp: datetime):
    global _CACHED_QUARANTINE_RESULT
    if _CACHED_QUARANTINE_RESULT is None:
        quarantine_request = QuarantineImportRequest(
            source_path=str(QUARANTINE_EXTERNAL),
            source_type=QuarantineSourceType.EXTERNAL_CANDIDATE_FIXTURE,
            requested_by="foundation-freeze-audit",
            source_reference="SKILL-01.8",
            import_reason="Foundation freeze contour",
            correlation_id="foundation-freeze",
        )
        _CACHED_QUARANTINE_RESULT = import_skill_package_to_quarantine(
            quarantine_request,
            quarantine_base_dir=Path(".tmp_foundation_freeze_quarantine"),
            imported_at=timestamp,
        )
    return _CACHED_QUARANTINE_RESULT


@dataclass(frozen=True)
class FoundationFreezeContour:
    """Deterministic in-memory Foundation contour snapshot."""

    package_hash: str
    registry_snapshot_hash: str
    audit_report_hash: str
    lineage_graph_hash: str
    decision_readiness: str
    blockers: tuple[str, ...]
    lifecycle_statuses: dict[str, str]
    tenant_visibility: dict[str, bool]
    execution_eligible: bool
    package_validation_graph_hash: str
    quarantine_graph_hash: str
    connector_policy_outcome: str


def build_foundation_freeze_contour(
    *,
    recorded_at: datetime | None = None,
) -> FoundationFreezeContour:
    timestamp = recorded_at or FIXED_TIME

    package_hash = calculate_skill_package_hash(FROZEN_PACKAGE)
    validation_report = _cached_validation_report()
    package_audit = adapt_package_validation_report(validation_report, generated_at=timestamp)
    validation_graph = build_package_validation_lineage(
        validation_report,
        audit_report=package_audit,
    )

    projection = project_validation_report(validation_report, recorded_at=timestamp)
    if projection.version_record is None:
        raise RuntimeError("Frozen package must project to registry version record.")
    snapshot = build_registry_snapshot(
        [projection.version_record],
        generated_at=timestamp,
        snapshot_id="foundation-freeze-snapshot",
    )
    registry_graph = build_registry_projection_lineage(
        projection,
        snapshot=snapshot,
        validation_graph=validation_graph,
    )

    quarantine_result = _cached_quarantine_result(timestamp=timestamp)
    quarantine_audit = adapt_quarantine_import_result(quarantine_result, generated_at=timestamp)
    quarantine_graph = build_quarantine_lineage(quarantine_result, audit_report=quarantine_audit)

    gateway, _adapters = build_test_gateway()
    connector_request = ConnectorExecutionRequest(
        request_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        correlation_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        tenant_id=UUID(TENANT_A),
        project_id=PROJECT_ID,
        actor_id=ACTOR_ID,
        skill_id="ms.skill.market_validation",
        skill_version="0.1.0",
        connector_id=RESEARCH_CONNECTOR_ID,
        connector_version=CONNECTOR_VERSION,
        tool_id=RESEARCH_TOOL_ID,
        input_payload={"query": "foundation-freeze"},
        requested_at=timestamp,
        skill_allowed_tools=(),
    )
    _, _, policy_decision = gateway.evaluate_policy(
        connector_request,
        tenant_binding=None,
        project_binding=None,
    )
    connector_audit = adapt_connector_policy_decision(
        policy_decision,
        target=connector_policy_target(),
        generated_at=timestamp,
    )
    connector_graph = build_connector_request_lineage(
        connector_request,
        policy_decision,
        audit_report=connector_audit,
    )

    composite_target = AuditTargetReference(
        target_type=AuditTargetType.SKILL_PACKAGE,
        target_id=validation_report.skill_id,
        target_version=validation_report.skill_version,
        package_hash=package_hash,
        lifecycle_status=SkillLifecycleStatus.CANDIDATE.value,
    )
    composite_audit = aggregate_audit_reports(
        composite_target,
        (package_audit, quarantine_audit, connector_audit),
        generated_at=timestamp,
    )
    audit_lineage = build_audit_lineage(composite_audit)
    lineage_graph = combine_lineage_graphs(registry_graph, connector_graph, audit_lineage)

    eligibility = derive_eligibility_view(
        projection.version_record,
        tenant_id=TENANT_A,
        view=SkillRegistryView.NORMAL,
    )

    lifecycle_statuses = {
        "frozen_package": SkillLifecycleStatus.CANDIDATE.value,
        "quarantine_effective": quarantine_result.effective_status.value
        if quarantine_result.effective_status
        else "unknown",
        "registry_projection": projection.version_record.lifecycle_status.value,
    }
    tenant_visibility = {
        "frozen_global_visible": derive_eligibility_view(
            projection.version_record,
            tenant_id=TENANT_A,
            view=SkillRegistryView.NORMAL,
        ).visible_to_tenant,
        "quarantine_not_production": not derive_eligibility_view(
            projection.version_record,
            tenant_id=TENANT_A,
            view=SkillRegistryView.NORMAL,
        ).production_eligible,
    }

    return FoundationFreezeContour(
        package_hash=package_hash,
        registry_snapshot_hash=snapshot.snapshot_hash,
        audit_report_hash=composite_audit.report_hash,
        lineage_graph_hash=lineage_graph.graph_hash,
        decision_readiness=composite_audit.decision_readiness.value,
        blockers=tuple(composite_audit.blockers),
        lifecycle_statuses=lifecycle_statuses,
        tenant_visibility=tenant_visibility,
        execution_eligible=eligibility.selectable_for_new_work,
        package_validation_graph_hash=validation_graph.graph_hash,
        quarantine_graph_hash=quarantine_graph.graph_hash,
        connector_policy_outcome=policy_decision.outcome.value,
    )


FOUNDATION_VERSIONS = {
    "validator_version": VALIDATOR_VERSION,
    "registry_schema_version": "0.1.0",
    "audit_schema_version": "0.1.0",
    "lineage_schema_version": "0.1.0",
    "frozen_package_hash": "6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133",
}
