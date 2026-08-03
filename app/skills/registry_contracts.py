"""Immutable Skill registry read models (SKILL-01.3)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.contracts import (
    SkillLifecycleStatus,
    SkillProvenance,
    SkillSourceType,
    SkillTenantScope,
)
from app.skills.validation_contracts import SkillValidationIssue

REGISTRY_SCHEMA_VERSION = "0.1.0"


class SkillValidationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


class SkillProjectionOutcome(StrEnum):
    PROJECTED = "projected"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    INCOMPLETE = "incomplete"


class SkillApprovalState(StrEnum):
    UNKNOWN = "unknown"
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    GRANTED = "granted"
    DENIED = "denied"


class SkillSecurityClass(StrEnum):
    READ_ONLY_CANDIDATE = "read_only_candidate"
    QUARANTINED = "quarantined"
    AUDITED = "audited"
    APPROVED = "approved"
    ACTIVE = "active"
    RESTRICTED = "restricted"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class SkillRegistryView(StrEnum):
    NORMAL = "normal"
    AUDIT = "audit"
    INTERNAL_RESEARCH = "internal_research"


class SkillRegistrySourceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    package_hash: str = Field(min_length=64, max_length=64)
    validator_version: str
    validation_status: SkillValidationStatus
    validation_mode: str
    validated_at: datetime
    warning_count: int = 0
    security_finding_count: int = 0


class SkillDependencyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    dependency_id: str
    relationship: str
    note: str | None = None


class SkillCapabilityRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability_id: str


class SkillRegistryVersionRecord(BaseModel):
    """Immutable registry entry for one skill_id + version."""

    model_config = ConfigDict(frozen=True)

    skill_id: str
    version: str
    name: str
    lifecycle_status: SkillLifecycleStatus
    source_type: SkillSourceType
    tenant_scope: SkillTenantScope
    owner: str
    owner_tenant_id: str | None = None
    capabilities: tuple[str, ...]
    dependencies: tuple[SkillDependencyRecord, ...]
    runtime_compatibility: tuple[str, ...]
    quality_state: str | None = None
    package_hash: str
    validator_version: str
    validation_status: SkillValidationStatus
    provenance: SkillProvenance
    normalized_manifest: dict[str, Any]
    source_reference: SkillRegistrySourceReference
    security_class: SkillSecurityClass
    approval_state: SkillApprovalState = SkillApprovalState.UNKNOWN
    evidence_policy_summary: str | None = None
    approval_policy_summary: str | None = None
    warnings: tuple[SkillValidationIssue, ...] = ()
    security_findings: tuple[SkillValidationIssue, ...] = ()
    recorded_at: datetime


class SkillRegistryRecord(BaseModel):
    """Aggregated read model for a logical Skill identity."""

    model_config = ConfigDict(frozen=True)

    skill_id: str
    name: str
    latest_known_version: str | None = None
    available_versions: tuple[str, ...] = ()
    lifecycle_status: SkillLifecycleStatus
    source_type: SkillSourceType
    tenant_scope: SkillTenantScope
    owner: str
    owner_tenant_id: str | None = None
    capabilities: tuple[str, ...]
    dependencies: tuple[SkillDependencyRecord, ...]
    runtime_compatibility: tuple[str, ...]
    quality_state: str | None = None
    package_hash: str | None = None
    validator_version: str | None = None
    validation_status: SkillValidationStatus | None = None
    provenance: SkillProvenance | None = None
    created_at: datetime
    updated_at: datetime
    deprecated_by: str | None = None
    archived: bool = False
    security_class: SkillSecurityClass
    approval_state: SkillApprovalState = SkillApprovalState.UNKNOWN
    evidence_policy_summary: str | None = None
    approval_policy_summary: str | None = None
    versions: tuple[SkillRegistryVersionRecord, ...] = ()


class SkillRegistryProjectionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: SkillProjectionOutcome
    reason_code: str
    version_record: SkillRegistryVersionRecord | None = None
    explanation: str | None = None
    remediation_hint: str | None = None


class SkillRegistryConflict(BaseModel):
    model_config = ConfigDict(frozen=True)

    conflict_code: str
    severity: str
    involved_records: tuple[str, ...]
    explanation: str
    remediation_hint: str | None = None


class SkillEligibilityView(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    version: str
    production_eligible: bool
    selectable_for_new_work: bool
    visible_to_tenant: bool
    lineage_resolvable: bool
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class SkillRegistryQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str | None = None
    version: str | None = None
    lifecycle_status: SkillLifecycleStatus | None = None
    source_type: SkillSourceType | None = None
    tenant_scope: SkillTenantScope | None = None
    capability: str | None = None
    runtime_compatibility: str | None = None
    owner: str | None = None
    package_hash: str | None = None
    validation_status: SkillValidationStatus | None = None
    tenant_id: str | None = None
    view: SkillRegistryView = SkillRegistryView.NORMAL


class SkillRegistryQueryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    records: tuple[SkillRegistryRecord, ...]
    total_count: int


class SkillRegistrySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    generated_at: datetime
    records: tuple[SkillRegistryRecord, ...]
    source_hashes: tuple[str, ...]
    registry_schema_version: str = REGISTRY_SCHEMA_VERSION
    record_count: int
    capability_index: dict[str, tuple[str, ...]]
    tenant_scope_index: dict[str, tuple[str, ...]]
    lifecycle_status_index: dict[str, tuple[str, ...]]
    snapshot_hash: str


_SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_semver(version: str) -> tuple[int, int, int]:
    match = _SEMVER_PATTERN.match(version)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def canonical_registry_json(payload: Any) -> str:
    """Deterministic UTF-8 JSON for registry models."""

    def _default(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat()
        raise TypeError(f"Unsupported type for canonical JSON: {type(value)!r}")

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_default)


def canonical_model_dict(model: BaseModel) -> dict[str, Any]:
    return json.loads(canonical_registry_json(model.model_dump(mode="json")))


def compute_snapshot_hash(snapshot: SkillRegistrySnapshot) -> str:
    payload = {
        "registry_schema_version": snapshot.registry_schema_version,
        "generated_at": snapshot.generated_at.astimezone(UTC).isoformat(),
        "records": [canonical_model_dict(record) for record in snapshot.records],
        "source_hashes": list(snapshot.source_hashes),
    }
    encoded = canonical_registry_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
