"""Validation report contracts for SKILL-01.2 package validator."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.contracts import SkillLifecycleStatus, SkillManifest

VALIDATOR_VERSION = "0.1.0"


class SkillValidationMode(StrEnum):
    """Validation strictness profile."""

    CANDIDATE = "candidate"
    QUARANTINE_IMPORT = "quarantine_import"
    REGISTRY_READINESS = "registry_readiness"


class SkillValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class SkillValidationIssue(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    severity: SkillValidationSeverity
    message: str = Field(min_length=1, max_length=2000)
    location: str | None = Field(default=None, max_length=512)
    rule_reference: str | None = Field(default=None, max_length=128)
    remediation_hint: str | None = Field(default=None, max_length=1000)


class SkillValidationCheck(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    passed: bool
    detail: str | None = Field(default=None, max_length=1000)


class SkillSchemaValidationResult(BaseModel):
    schema_ref: str
    valid: bool
    draft: str | None = None
    errors: list[str] = Field(default_factory=list)


class SkillPackageValidationReport(BaseModel):
    package_path: str
    skill_id: str | None = None
    skill_version: str | None = None
    status: SkillLifecycleStatus | None = None
    valid: bool = False
    validation_mode: SkillValidationMode
    package_hash: str | None = None
    normalized_manifest: dict[str, Any] | None = None
    errors: list[SkillValidationIssue] = Field(default_factory=list)
    warnings: list[SkillValidationIssue] = Field(default_factory=list)
    checks: list[SkillValidationCheck] = Field(default_factory=list)
    referenced_files: list[str] = Field(default_factory=list)
    missing_files: list[str] = Field(default_factory=list)
    forbidden_files: list[str] = Field(default_factory=list)
    schema_results: list[SkillSchemaValidationResult] = Field(default_factory=list)
    security_findings: list[SkillValidationIssue] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    validator_version: str = VALIDATOR_VERSION
    manifest: SkillManifest | None = None

    def add_error(
        self,
        *,
        code: str,
        message: str,
        location: str | None = None,
        rule_reference: str | None = None,
        remediation_hint: str | None = None,
    ) -> None:
        issue = SkillValidationIssue(
            code=code,
            severity=SkillValidationSeverity.ERROR,
            message=message,
            location=location,
            rule_reference=rule_reference,
            remediation_hint=remediation_hint,
        )
        self.errors.append(issue)
        if code.startswith("security_"):
            self.security_findings.append(issue)

    def add_warning(
        self,
        *,
        code: str,
        message: str,
        location: str | None = None,
        rule_reference: str | None = None,
        remediation_hint: str | None = None,
    ) -> None:
        self.warnings.append(
            SkillValidationIssue(
                code=code,
                severity=SkillValidationSeverity.WARNING,
                message=message,
                location=location,
                rule_reference=rule_reference,
                remediation_hint=remediation_hint,
            )
        )

    def add_check(self, name: str, passed: bool, detail: str | None = None) -> None:
        self.checks.append(SkillValidationCheck(name=name, passed=passed, detail=detail))

    def finalize(self) -> SkillPackageValidationReport:
        self.valid = len(self.errors) == 0
        return self
