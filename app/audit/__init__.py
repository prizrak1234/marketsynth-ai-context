"""Unified audit report layer (SKILL-01.6).

Normalizes findings from package validation, quarantine import, registry
projection/conflicts and connector policy into one machine-readable report.
No persistence, API, UI or lifecycle mutation in this phase.
"""

from app.audit.adapters import (
    adapt_connector_evidence_descriptor,
    adapt_connector_execution_result_schema_support,
    adapt_connector_policy_decision,
    adapt_package_validation_report,
    adapt_quarantine_import_result,
    adapt_registry_conflict,
    adapt_registry_projection_result,
    hash_source_payload,
)
from app.audit.aggregator import aggregate_audit_reports
from app.audit.classifications import (
    BLOCKING_SOURCE_CODES,
    derive_blocking_flags,
    derive_overall_severity,
    map_connector_policy_outcome,
    map_package_validator_severity,
    map_quarantine_static_code_severity,
    map_registry_conflict_severity,
)
from app.audit.contracts import (
    ADAPTER_VERSION,
    AUDIT_SCHEMA_VERSION,
    AuditDecisionReadiness,
    AuditEvidenceReference,
    AuditFinding,
    AuditFindingCategory,
    AuditFindingSeverity,
    AuditGenerationMode,
    AuditOverallSeverity,
    AuditProvenance,
    AuditRecommendation,
    AuditRecommendationType,
    AuditReportStatus,
    AuditSourceReference,
    AuditSourceSystem,
    AuditTargetReference,
    AuditTargetType,
    AuditType,
    UnifiedAuditReport,
    validate_audit_type,
    validate_finding_category,
)
from app.audit.errors import (
    AuditAdapterError,
    AuditAggregationError,
    AuditContractError,
    AuditError,
)
from app.audit.readiness import derive_decision_readiness
from app.audit.redaction import redact_payload, redact_text, sanitize_location
from app.audit.serialization import (
    canonical_json,
    compute_report_hash,
    deduplicate_findings,
    serialize_report,
)

__all__ = [
    "ADAPTER_VERSION",
    "AUDIT_SCHEMA_VERSION",
    "AuditAdapterError",
    "AuditAggregationError",
    "AuditContractError",
    "AuditDecisionReadiness",
    "AuditError",
    "AuditEvidenceReference",
    "AuditFinding",
    "AuditFindingCategory",
    "AuditFindingSeverity",
    "AuditGenerationMode",
    "AuditOverallSeverity",
    "AuditProvenance",
    "AuditRecommendation",
    "AuditRecommendationType",
    "AuditReportStatus",
    "AuditSourceReference",
    "AuditSourceSystem",
    "AuditTargetReference",
    "AuditTargetType",
    "AuditType",
    "BLOCKING_SOURCE_CODES",
    "UnifiedAuditReport",
    "adapt_connector_evidence_descriptor",
    "adapt_connector_execution_result_schema_support",
    "adapt_connector_policy_decision",
    "adapt_package_validation_report",
    "adapt_quarantine_import_result",
    "adapt_registry_conflict",
    "adapt_registry_projection_result",
    "aggregate_audit_reports",
    "canonical_json",
    "compute_report_hash",
    "deduplicate_findings",
    "derive_blocking_flags",
    "derive_decision_readiness",
    "derive_overall_severity",
    "hash_source_payload",
    "map_connector_policy_outcome",
    "map_package_validator_severity",
    "map_quarantine_static_code_severity",
    "map_registry_conflict_severity",
    "redact_payload",
    "redact_text",
    "sanitize_location",
    "serialize_report",
    "validate_audit_type",
    "validate_finding_category",
]
