"""Immutable unified audit report contracts (SKILL-01.6)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AUDIT_SCHEMA_VERSION = "0.1.0"
ADAPTER_VERSION = "0.1.0"


class AuditTargetType(StrEnum):
    SKILL_PACKAGE = "skill_package"
    SKILL_IMPORT = "skill_import"
    SKILL_REGISTRY_RECORD = "skill_registry_record"
    SKILL_REGISTRY_SNAPSHOT = "skill_registry_snapshot"
    CONNECTOR = "connector"
    CONNECTOR_TOOL = "connector_tool"
    CONNECTOR_REQUEST = "connector_request"
    CONNECTOR_POLICY_DECISION = "connector_policy_decision"


class AuditType(StrEnum):
    PACKAGE_VALIDATION = "package_validation"
    QUARANTINE_IMPORT = "quarantine_import"
    REGISTRY_CONSISTENCY = "registry_consistency"
    CONNECTOR_POLICY = "connector_policy"
    COMPOSITE_FOUNDATION_AUDIT = "composite_foundation_audit"


class AuditReportStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    CONFLICTED = "conflicted"


class AuditOverallSeverity(StrEnum):
    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditFindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditFindingCategory(StrEnum):
    STRUCTURE = "structure"
    SCHEMA = "schema"
    SECURITY = "security"
    PERMISSIONS = "permissions"
    LIFECYCLE = "lifecycle"
    PROVENANCE = "provenance"
    LICENSING = "licensing"
    TENANT_ISOLATION = "tenant_isolation"
    CONNECTOR_POLICY = "connector_policy"
    CREDENTIAL_BOUNDARY = "credential_boundary"
    EVIDENCE = "evidence"
    APPROVAL = "approval"
    IDEMPOTENCY = "idempotency"
    BUDGET = "budget"
    RATE_LIMIT = "rate_limit"
    CONFLICT = "conflict"
    COMPATIBILITY = "compatibility"
    UNKNOWN = "unknown"


class AuditDecisionReadiness(StrEnum):
    NOT_READY = "not_ready"
    READY_FOR_HUMAN_REVIEW = "ready_for_human_review"
    READY_FOR_AUDIT = "ready_for_audit"
    READY_FOR_APPROVAL_REVIEW = "ready_for_approval_review"
    BLOCKED = "blocked"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class AuditSourceSystem(StrEnum):
    SKILL_PACKAGE_VALIDATOR = "skill_package_validator"
    QUARANTINE_IMPORT_ADAPTER = "quarantine_import_adapter"
    SKILL_REGISTRY_PROJECTION = "skill_registry_projection"
    SKILL_REGISTRY_CONFLICT_DETECTOR = "skill_registry_conflict_detector"
    CONNECTOR_POLICY_ENGINE = "connector_policy_engine"
    CONNECTOR_GATEWAY = "connector_gateway"
    CONNECTOR_EVIDENCE_DESCRIPTOR = "connector_evidence_descriptor"


class AuditGenerationMode(StrEnum):
    AUTOMATED_STATIC = "automated_static"
    AUTOMATED_POLICY = "automated_policy"
    COMPOSITE = "composite"
    MANUAL_REVIEW_IMPORTED = "manual_review_imported"


class AuditRecommendationType(StrEnum):
    FIX_MANIFEST = "fix_manifest"
    REMOVE_FORBIDDEN_FILE = "remove_forbidden_file"
    VERIFY_LICENSE = "verify_license"
    VERIFY_AUTHOR = "verify_author"
    ADD_PROVENANCE = "add_provenance"
    RESOLVE_IDENTITY_CONFLICT = "resolve_identity_conflict"
    REQUEST_OWNER_REVIEW = "request_owner_review"
    REQUEST_SECURITY_REVIEW = "request_security_review"
    REQUEST_LEGAL_REVIEW = "request_legal_review"
    REQUEST_APPROVAL = "request_approval"
    ADD_BUDGET_CONTEXT = "add_budget_context"
    ADD_IDEMPOTENCY_SUPPORT = "add_idempotency_support"
    DEFER = "defer"
    REJECT_CANDIDATE = "reject_candidate"


class AuditTargetReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_type: AuditTargetType
    target_id: str | None = None
    target_version: str | None = None
    package_hash: str | None = None
    tenant_id: str | None = None
    project_id: str | None = None
    source_type: str | None = None
    lifecycle_status: str | None = None
    connector_id: str | None = None
    tool_id: str | None = None
    import_id: str | None = None
    snapshot_id: str | None = None


class AuditEvidenceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str
    evidence_kind: str = "connector_descriptor"
    input_hash: str | None = None
    output_hash: str | None = None
    provider_metadata_hash: str | None = None
    lineage_parent_ids: tuple[str, ...] = ()
    external_reference_id: str | None = None


class AuditFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str
    source_system: AuditSourceSystem
    source_code: str
    category: AuditFindingCategory
    severity: AuditFindingSeverity
    title: str
    message: str
    location: str | None = None
    rule_reference: str | None = None
    remediation_hint: str | None = None
    blocking: bool = False
    execution_blocking: bool = False
    resolved: bool = False
    evidence_references: tuple[AuditEvidenceReference, ...] = ()
    related_target_ids: tuple[str, ...] = ()
    source_payload_hash: str | None = None
    created_at: datetime


class AuditSourceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_system: AuditSourceSystem
    source_report_id: str
    source_version: str
    source_hash: str
    generated_at: datetime
    adapter_version: str = ADAPTER_VERSION


class AuditRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    recommendation_type: AuditRecommendationType
    message: str
    related_finding_ids: tuple[str, ...] = ()


class AuditProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    generated_by: str
    generation_mode: AuditGenerationMode
    source_systems: tuple[AuditSourceSystem, ...]
    target_source: str | None = None
    tenant_context: str | None = None
    project_context: str | None = None
    correlation_id: str | None = None
    parent_audit_ids: tuple[str, ...] = ()
    methodology_version: str = AUDIT_SCHEMA_VERSION
    human_review_required: bool = False
    owner_decision_required: bool = False


class UnifiedAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    audit_id: UUID
    audit_type: AuditType
    target: AuditTargetReference
    status: AuditReportStatus
    overall_severity: AuditOverallSeverity
    decision_readiness: AuditDecisionReadiness
    findings: tuple[AuditFinding, ...] = ()
    source_reports: tuple[AuditSourceReference, ...] = ()
    evidence_references: tuple[AuditEvidenceReference, ...] = ()
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    recommendations: tuple[AuditRecommendation, ...] = ()
    provenance: AuditProvenance
    generated_at: datetime
    audit_schema_version: str = AUDIT_SCHEMA_VERSION
    adapter_versions: dict[str, str] = Field(default_factory=dict)
    report_hash: str = ""


def validate_audit_type(value: str) -> AuditType:
    try:
        return AuditType(value)
    except ValueError as exc:
        raise ValueError(f"Unknown audit type: {value}") from exc


def validate_finding_category(value: str) -> AuditFindingCategory:
    try:
        return AuditFindingCategory(value)
    except ValueError as exc:
        raise ValueError(f"Unknown finding category: {value}") from exc
