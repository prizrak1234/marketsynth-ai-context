"""Immutable Connector Gateway contracts (SKILL-01.5)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ConnectorId = str
ConnectorVersion = str
ConnectorToolId = str


class ConnectorStatus(StrEnum):
    CANDIDATE = "candidate"
    QUARANTINED = "quarantined"
    AUDITED = "audited"
    APPROVED = "approved"
    ACTIVE = "active"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    REJECTED = "rejected"


_ACCEPTED_CONNECTOR_STATUSES = frozenset(ConnectorStatus)


class ConnectorClass(StrEnum):
    RESEARCH = "research"
    CONTENT_GENERATION = "content_generation"
    PUBLICATION = "publication"
    ANALYTICS = "analytics"
    CRM = "crm"
    ADVERTISING = "advertising"
    STORAGE = "storage"
    DEVELOPMENT = "development"
    COLLABORATION = "collaboration"


class ConnectorActionType(StrEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    PUBLISH = "publish"
    EXECUTE = "execute"
    BILLING = "billing"


class ConnectorSideEffectClass(StrEnum):
    NONE = "none"
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    EXTERNALLY_VISIBLE = "externally_visible"
    FINANCIALLY_SENSITIVE = "financially_sensitive"


class ConnectorDataSensitivity(StrEnum):
    PUBLIC = "public"
    TENANT_INTERNAL = "tenant_internal"
    PERSONAL = "personal"
    CONFIDENTIAL = "confidential"
    CREDENTIAL_ADJACENT = "credential_adjacent"


class ConnectorApprovalClass(StrEnum):
    NONE = "none"
    USER_CONFIRMATION = "user_confirmation"
    OWNER_APPROVAL = "owner_approval"
    ELEVATED_APPROVAL = "elevated_approval"


class ConnectorIdempotencyClass(StrEnum):
    GUARANTEED = "guaranteed"
    SUPPORTED_BY_KEY = "supported_by_key"
    PROVIDER_BEST_EFFORT = "provider_best_effort"
    UNKNOWN = "unknown"
    NOT_IDEMPOTENT = "not_idempotent"


class ConnectorHealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ConnectorPolicyOutcome(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_ADDITIONAL_CONTEXT = "require_additional_context"
    DEFER = "defer"
    UNAVAILABLE = "unavailable"


class ConnectorExecutionResultStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED_BY_POLICY = "rejected_by_policy"
    APPROVAL_REQUIRED = "approval_required"
    UNAVAILABLE = "unavailable"
    TIMED_OUT = "timed_out"
    RATE_LIMITED = "rate_limited"
    DUPLICATE_PREVENTED = "duplicate_prevented"
    UNKNOWN_OUTCOME = "unknown_outcome"


class ConnectorCapability(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    capability_id: str
    description: str = ""


class ConnectorRateLimitDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    requests_per_minute: int | None = None
    burst_limit: int | None = None
    retry_after_support: bool = False


class ConnectorCostEstimate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    currency: str
    estimated_min: float | None = None
    estimated_max: float | None = None
    unit: str = "request"
    pricing_source: str = "unknown"
    estimate_confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    observed_cost_available: bool = False


class ConnectorIdempotencyDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    idempotency_class: ConnectorIdempotencyClass
    idempotency_key_required: bool = False
    duplicate_side_effect_risk: bool = False


class ConnectorToolDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    connector_id: ConnectorId
    tool_id: ConnectorToolId
    name: str
    description: str = ""
    input_schema_reference: str = ""
    output_schema_reference: str = ""
    required_capabilities: tuple[str, ...] = ()
    action_type: ConnectorActionType
    side_effect_class: ConnectorSideEffectClass
    data_sensitivity: ConnectorDataSensitivity
    approval_class: ConnectorApprovalClass
    billing_sensitive: bool = False
    publication_sensitive: bool = False
    destructive: bool = False
    idempotency: ConnectorIdempotencyClass
    rate_limit_profile: str = "default"
    cost_profile: str = "default"
    evidence_requirements: tuple[str, ...] = ()
    enabled_by_default: bool = False


class ConnectorAdapterDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter_id: str
    adapter_kind: Literal["synthetic", "native", "mcp_derived", "provider_sdk"] = "synthetic"
    version: str = "0.0.0"
    supports_dry_run: bool = False


class ConnectorDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    connector_id: ConnectorId
    connector_version: ConnectorVersion
    name: str
    description: str = ""
    status: ConnectorStatus
    primary_class: ConnectorClass
    secondary_capabilities: tuple[ConnectorCapability, ...] = ()
    adapter: ConnectorAdapterDescriptor
    health_state: ConnectorHealthState = ConnectorHealthState.UNKNOWN
    is_mcp: bool = False
    is_native_authoritative: bool = False
    fixture_only: bool = False
    runtime_compatible: tuple[str, ...] = ("operator_dry_run",)


class CredentialBindingReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    binding_id: str
    tenant_id: UUID
    provider: str
    connector_id: ConnectorId
    scope_names: tuple[str, ...] = ()
    status: Literal["active", "expired", "revoked", "pending"] = "active"
    expires_at: datetime | None = None
    rotated_at: datetime | None = None
    project_allowlist: tuple[str, ...] = ()
    metadata_only: bool = True


class TenantConnectorBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: UUID
    connector_id: ConnectorId
    connector_version: ConnectorVersion
    visible: bool = True
    enabled_tool_ids: frozenset[ConnectorToolId] = Field(default_factory=frozenset)
    credential_binding_id: str | None = None
    runtime_compatible: tuple[str, ...] = ("operator_dry_run",)


class ProjectConnectorBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: UUID
    project_id: UUID
    connector_id: ConnectorId
    connector_version: ConnectorVersion
    enabled_tool_ids: frozenset[ConnectorToolId] = Field(default_factory=frozenset)
    credential_binding_id: str | None = None


class BudgetPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_budget_limit: float | None = None
    project_budget_limit: float | None = None
    request_budget_limit: float | None = None
    approval_threshold: float | None = None
    deny_above_limit: bool = True


class RetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_attempts: int = 1
    retryable_statuses: tuple[ConnectorExecutionResultStatus, ...] = ()
    backoff_policy: str = "none"
    retry_after_support: bool = False
    duplicate_side_effect_risk: bool = False
    idempotency_required: bool = False


class TimeoutPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timeout_seconds: float = 30.0


class ConnectorExecutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: UUID
    correlation_id: UUID
    tenant_id: UUID
    project_id: UUID
    actor_id: UUID
    skill_id: str | None = None
    skill_version: str | None = None
    connector_id: ConnectorId
    connector_version: ConnectorVersion
    tool_id: ConnectorToolId
    input_payload: dict[str, Any] = Field(default_factory=dict)
    credential_binding_reference: CredentialBindingReference | None = None
    approval_reference: str | None = None
    evidence_context: dict[str, Any] = Field(default_factory=dict)
    budget_context: BudgetPolicy | None = None
    idempotency_key: str | None = None
    requested_at: datetime
    timeout_policy: TimeoutPolicy = Field(default_factory=TimeoutPolicy)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    dry_run: bool = False
    runtime_id: str = "operator_dry_run"
    skill_allowed_tools: tuple[str, ...] = ()


class ConnectorExecutionError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    safe_details: dict[str, Any] = Field(default_factory=dict)


class ConnectorEvidenceDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: UUID
    request_id: UUID
    connector_id: ConnectorId
    connector_version: ConnectorVersion
    tool_id: ConnectorToolId
    skill_id: str | None = None
    skill_version: str | None = None
    tenant_id: UUID
    project_id: UUID
    action_type: ConnectorActionType
    side_effect_class: ConnectorSideEffectClass
    approval_reference: str | None = None
    external_reference_id: str | None = None
    input_hash: str
    output_hash: str
    provider_metadata_hash: str
    cost_observed: float | None = None
    started_at: datetime
    finished_at: datetime
    result_status: ConnectorExecutionResultStatus
    lineage_parent_ids: tuple[str, ...] = ()


class ConnectorPolicyFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    check_id: str
    passed: bool
    message: str = ""
    severity: Literal["info", "warning", "error"] = "error"


class ConnectorPolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: ConnectorPolicyOutcome
    findings: tuple[ConnectorPolicyFinding, ...] = ()
    effective_tool_allowed: bool = False
    approval_required: bool = False
    reason: str = ""


class ConnectorExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: UUID
    connector_id: ConnectorId
    connector_version: ConnectorVersion
    tool_id: ConnectorToolId
    status: ConnectorExecutionResultStatus
    output_payload: dict[str, Any] = Field(default_factory=dict)
    safe_provider_metadata: dict[str, Any] = Field(default_factory=dict)
    external_reference_id: str | None = None
    idempotency_observed: bool | None = None
    cost_observed: float | None = None
    rate_limit_observed: dict[str, Any] | None = None
    evidence_descriptor: ConnectorEvidenceDescriptor | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    retry_count: int = 0
    error: ConnectorExecutionError | None = None
    side_effect_observed: ConnectorSideEffectClass | None = None
    approval_reference: str | None = None
    skill_id: str | None = None
    skill_version: str | None = None


def validate_connector_status(value: str) -> ConnectorStatus:
    try:
        status = ConnectorStatus(value)
    except ValueError as exc:
        raise ValueError(f"Unknown connector status: {value}") from exc
    if status not in _ACCEPTED_CONNECTOR_STATUSES:
        raise ValueError(f"Unknown connector status: {value}")
    return status


_SECRET_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "client_secret",
    "refresh_token",
    "credential",
)


def payload_contains_secret_like_keys(payload: dict[str, Any], *, prefix: str = "") -> str | None:
    for key, value in payload.items():
        lowered = key.lower()
        if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
            return f"{prefix}{key}"
        if isinstance(value, dict):
            nested = payload_contains_secret_like_keys(value, prefix=f"{prefix}{key}.")
            if nested:
                return nested
    return None


def credential_reference_contains_secret_material(binding: CredentialBindingReference) -> bool:
    for field_name in binding.model_fields:
        if field_name in {"metadata_only"}:
            continue
        value = getattr(binding, field_name)
        if isinstance(value, str) and any(
            fragment in value.lower() for fragment in _SECRET_KEY_FRAGMENTS
        ) and field_name not in {"provider", "connector_id", "binding_id"}:
            return True
    return False
