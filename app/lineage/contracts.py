"""Immutable lineage contracts (SKILL-01.7)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

LINEAGE_SCHEMA_VERSION = "0.1.0"

LineageNodeId = str


class LineageNodeType(StrEnum):
    SKILL_PACKAGE = "skill_package"
    SKILL_VERSION = "skill_version"
    PACKAGE_VALIDATION = "package_validation"
    QUARANTINE_IMPORT = "quarantine_import"
    REGISTRY_PROJECTION = "registry_projection"
    REGISTRY_SNAPSHOT = "registry_snapshot"
    CONNECTOR_REQUEST = "connector_request"
    CONNECTOR_POLICY_DECISION = "connector_policy_decision"
    CONNECTOR_RESULT = "connector_result"
    CONNECTOR_EVIDENCE = "connector_evidence"
    UNIFIED_AUDIT_REPORT = "unified_audit_report"
    EXISTING_EVIDENCE = "existing_evidence"
    APPROVAL_REFERENCE = "approval_reference"
    PROJECT_SNAPSHOT = "project_snapshot"
    EXECUTION_RECORD = "execution_record"


class LineageEdgeType(StrEnum):
    DERIVED_FROM = "derived_from"
    VALIDATED_BY = "validated_by"
    IMPORTED_AS = "imported_as"
    PROJECTED_TO = "projected_to"
    INCLUDED_IN = "included_in"
    REQUESTED_BY = "requested_by"
    AUTHORIZED_BY = "authorized_by"
    DENIED_BY = "denied_by"
    EXECUTED_AS = "executed_as"
    PRODUCED = "produced"
    EVIDENCED_BY = "evidenced_by"
    AUDITED_BY = "audited_by"
    SUPERSEDES = "supersedes"
    VERSION_OF = "version_of"
    BELONGS_TO = "belongs_to"
    REFERENCES = "references"
    RESOLVED_BY = "resolved_by"


class LineageFindingCode(StrEnum):
    MISSING_PARENT = "missing_parent"
    ORPHAN_NODE = "orphan_node"
    HASH_MISMATCH = "hash_mismatch"
    TENANT_MISMATCH = "tenant_mismatch"
    PROJECT_MISMATCH = "project_mismatch"
    SKILL_IDENTITY_MISMATCH = "skill_identity_mismatch"
    CONNECTOR_REQUEST_MISSING = "connector_request_missing"
    CONNECTOR_RESULT_MISSING = "connector_result_missing"
    EVIDENCE_MISSING = "evidence_missing"
    APPROVAL_REFERENCE_MISSING = "approval_reference_missing"
    INVALID_EDGE = "invalid_edge"
    CYCLE_DETECTED = "cycle_detected"
    DUPLICATE_NODE_CONFLICT = "duplicate_node_conflict"
    SOURCE_REFERENCE_MISSING = "source_reference_missing"
    ARCHIVED_VERSION_UNRESOLVABLE = "archived_version_unresolvable"
    LIFECYCLE_SEMANTICS_CONFLICT = "lifecycle_semantics_conflict"
    AUDIT_SOURCE_MISSING = "audit_source_missing"


class LineageFindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LineageNodeReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: LineageNodeId
    node_type: LineageNodeType
    tenant_id: str | None = None
    project_id: str | None = None
    skill_id: str | None = None
    skill_version: str | None = None
    connector_id: str | None = None
    connector_version: str | None = None
    tool_id: str | None = None
    package_hash: str | None = None
    report_hash: str | None = None
    evidence_id: str | None = None
    external_reference_id: str | None = None
    snapshot_id: str | None = None
    snapshot_hash: str | None = None
    lifecycle_status: str | None = None
    created_at: datetime | None = None
    source_system: str | None = None
    metadata_hash: str | None = None
    global_scope: bool = False


class LineageEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: str
    from_node_id: LineageNodeId
    to_node_id: LineageNodeId
    edge_type: LineageEdgeType
    metadata_hash: str | None = None


class LineageContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str | None = None
    project_id: str | None = None
    skill_id: str | None = None
    skill_version: str | None = None
    correlation_id: str | None = None


class LineageSourceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_system: str
    source_id: str
    source_hash: str
    adapter_version: str = LINEAGE_SCHEMA_VERSION


class LineageFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: LineageFindingCode
    severity: LineageFindingSeverity
    message: str
    node_id: str | None = None
    edge_id: str | None = None
    blocking: bool = False


class LineageValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    valid: bool
    findings: tuple[LineageFinding, ...] = ()
    node_count: int = 0
    edge_count: int = 0


class LineageGraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    nodes: tuple[LineageNodeReference, ...] = ()
    edges: tuple[LineageEdge, ...] = ()
    context: LineageContext | None = None
    source_references: tuple[LineageSourceReference, ...] = ()
    graph_hash: str = ""
    schema_version: str = LINEAGE_SCHEMA_VERSION


class SkillExecutionLineageDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: str
    skill_id: str
    skill_version: str
    package_hash: str
    registry_snapshot_id: str | None = None
    registry_snapshot_hash: str | None = None
    tenant_id: str | None = None
    project_id: str | None = None
    actor_id: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    parent_evidence_ids: tuple[str, ...] = ()
    approval_reference: str | None = None
    connector_request_ids: tuple[str, ...] = ()
    audit_report_ids: tuple[str, ...] = ()
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str = "prepared"


class ConnectorExecutionLineageDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    connector_id: str
    connector_version: str
    tool_id: str
    tenant_id: str | None = None
    project_id: str | None = None
    skill_id: str | None = None
    skill_version: str | None = None
    credential_binding_reference_id: str | None = None
    approval_reference: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    provider_metadata_hash: str | None = None
    external_reference_id: str | None = None
    result_status: str | None = None
    evidence_id: str | None = None
    parent_lineage_ids: tuple[str, ...] = ()


class AuditLineageDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    audit_id: str
    report_hash: str
    target_node_ids: tuple[str, ...] = ()
    source_report_ids: tuple[str, ...] = ()
    source_hashes: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    parent_audit_ids: tuple[str, ...] = ()
    generated_by: str
    generation_mode: str
    methodology_version: str = LINEAGE_SCHEMA_VERSION
    owner_decision_required: bool = False
    human_review_completed: bool = False


class EvidenceLineageReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str
    source_system: str
    source_hash: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    provider_metadata_hash: str | None = None
    lineage_parent_ids: tuple[str, ...] = ()
    external_reference_id: str | None = None


def validate_node_type(value: str) -> LineageNodeType:
    try:
        return LineageNodeType(value)
    except ValueError as exc:
        raise ValueError(f"Unknown lineage node type: {value}") from exc


def validate_edge_type(value: str) -> LineageEdgeType:
    try:
        return LineageEdgeType(value)
    except ValueError as exc:
        raise ValueError(f"Unknown lineage edge type: {value}") from exc
