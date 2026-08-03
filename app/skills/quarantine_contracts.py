"""Quarantine import contracts (SKILL-01.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.contracts import SkillLifecycleStatus
from app.skills.registry_contracts import SkillRegistryProjectionResult
from app.skills.validation_contracts import (
    SkillPackageValidationReport,
    SkillValidationIssue,
)

ADAPTER_VERSION = "0.1.0"

PLATFORM_NATIVE_SKILL_IDS = frozenset({"ms.skill.market_validation"})


class QuarantineSourceType(StrEnum):
    LOCAL_DIRECTORY = "local_directory"
    LOCAL_ARCHIVE = "local_archive"
    EXTERNAL_CANDIDATE_FIXTURE = "external_candidate_fixture"
    PLATFORM_RESEARCH_CANDIDATE = "platform_research_candidate"


class QuarantineImportOutcome(StrEnum):
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    INCOMPLETE = "incomplete"
    CONFLICT = "conflict"


class QuarantineStaticFindingSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class QuarantineStaticFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    severity: QuarantineStaticFindingSeverity
    message: str
    location: str | None = None
    rule_reference: str | None = None


class QuarantineImportLimits(BaseModel):
    max_total_bytes: int = 10 * 1024 * 1024
    max_single_file_bytes: int = 512 * 1024
    max_file_count: int = 256
    max_directory_depth: int = 12
    max_path_length: int = 240


class QuarantineImportRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_path: str
    source_type: QuarantineSourceType
    requested_by: str = Field(min_length=1, max_length=128)
    tenant_id: str | None = Field(default=None, max_length=128)
    project_id: str | None = Field(default=None, max_length=128)
    source_reference: str = Field(min_length=1, max_length=512)
    expected_skill_id: str | None = Field(default=None, max_length=128)
    expected_version: str | None = Field(default=None, max_length=32)
    declared_license: str | None = Field(default=None, max_length=64)
    import_reason: str = Field(min_length=1, max_length=1000)
    correlation_id: str = Field(min_length=1, max_length=128)

    @field_validator("source_path")
    @classmethod
    def reject_remote_urls(cls, value: str) -> str:
        lowered = value.lower()
        if lowered.startswith(("http://", "https://", "git://", "ssh://", "ftp://")):
            raise ValueError("Remote source paths are forbidden for quarantine import.")
        return value


class QuarantineTenantContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: str | None = None
    project_id: str | None = None


class QuarantineProvenanceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    import_id: str
    source_type: QuarantineSourceType
    source_reference: str
    original_path_hash: str
    source_fingerprint: str
    materialized_package_hash: str | None = None
    declared_author: str | None = None
    declared_license: str | None = None
    verified_author: str | None = None
    verified_license: str | None = None
    requested_by: str
    tenant_id: str | None = None
    project_id: str | None = None
    imported_at: datetime
    validator_version: str | None = None
    adapter_version: str = ADAPTER_VERSION
    source_claims: dict[str, Any] = Field(default_factory=dict)
    unresolved_claims: tuple[str, ...] = ()


class QuarantineImportResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    import_id: str
    outcome: QuarantineImportOutcome
    effective_status: SkillLifecycleStatus | None = None
    source_fingerprint: str | None = None
    materialized_package_hash: str | None = None
    package_validation_report: SkillPackageValidationReport | None = None
    provenance: QuarantineProvenanceRecord | None = None
    static_findings: tuple[QuarantineStaticFinding, ...] = ()
    errors: tuple[SkillValidationIssue, ...] = ()
    warnings: tuple[SkillValidationIssue, ...] = ()
    quarantine_path_reference: str | None = None
    registry_projection: SkillRegistryProjectionResult | None = None
    audit_required: bool = False
    approval_required: bool = True
    executable: bool = False
    production_eligible: bool = False
    tenant_visible: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    adapter_version: str = ADAPTER_VERSION


class QuarantineImportState(BaseModel):
    """In-memory import tracking for conflict detection (no persistence)."""

    seen_source_fingerprints: dict[str, str] = Field(default_factory=dict)
    seen_id_version_hashes: dict[tuple[str, str], str] = Field(default_factory=dict)
    reserved_import_paths: set[str] = Field(default_factory=set)

    model_config = ConfigDict(arbitrary_types_allowed=True)
