"""Test-only helpers for SKILL-01.0 package skeleton validation.

================================================================================
NOT PRODUCTION CODE — READ BEFORE EXTENDING
================================================================================

This module is a **temporary test-only helper** for SKILL-01.0 freeze checks.

It is NOT:
  - the production Skill package validator (see SKILL-01.2)
  - an authoritative YAML implementation
  - a runtime loader or registry reader

The minimal regex/scalar parsing here MUST NOT be reused as the canonical
manifest parser. **DEPRECATED for package validation** — use
``app.skills.package_validator.validate_skill_package`` (SKILL-01.2+).

This helper remains temporarily for SKILL-01.0 fixture/I/O tests only.

Domain contracts live in ``app/schemas/contracts.py`` (SKILL-01.1+).
"""

from __future__ import annotations

import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

PACKAGE_ROOT = (
    Path(__file__).resolve().parents[2] / "packages" / "skills" / "ms.skill.market_validation"
)

ALLOWED_PACKAGE_STATUSES = frozenset(
    {
        "candidate",
        "quarantined",
        "audited",
        "approved",
        "active",
        "suspended",
        "deprecated",
        "archived",
        "rejected",
        "tenant_private",
        "tenant_active",
    }
)

SKILL_01_0_ALLOWED_STATUSES = frozenset({"candidate", "quarantined"})

FORBIDDEN_SECRET_PATTERNS = re.compile(
    r"(api[_-]?key|secret|password|token|credential)\s*:",
    re.IGNORECASE,
)

REQUIRED_MANIFEST_KEYS = frozenset(
    {
        "id",
        "name",
        "version",
        "description",
        "owner",
        "source",
        "license",
        "status",
        "capabilities",
        "activation_conditions",
        "required_inputs",
        "output_schema",
        "required_evidence",
        "dependencies",
        "allowed_tools",
        "approval_policy",
        "tenant_scope",
        "quality_threshold",
        "known_limitations",
        "test_suite",
        "provenance",
    }
)

REQUIRED_PACKAGE_ENTRIES = (
    "SKILL.md",
    "manifest.yaml",
    "schemas/input.schema.json",
    "schemas/output.schema.json",
    "tests/eval_manifest.yaml",
)


class MarketValidationVerdict(StrEnum):
    PROCEED = "proceed"
    PROCEED_WITH_CONDITIONS = "proceed_with_conditions"
    REVISE = "revise"
    DEFER = "defer"
    STOP = "stop"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class TraceItem(BaseModel):
    statement: str
    trace_type: str
    evidence_class: str | None = None
    source_ref: str | None = None
    confidence: str | None = None


class RiskItem(BaseModel):
    title: str
    description: str
    linked_trace_types: list[str] | None = None


class OutputProvenance(BaseModel):
    skill_id: str
    skill_version: str
    generated_at: str | None = None
    methodology_ref: str | None = None


class MarketValidationOutputFixture(BaseModel):
    skill_id: str
    skill_version: str
    verdict: MarketValidationVerdict
    verdict_confidence: str
    executive_summary: str
    supporting_evidence: list[TraceItem]
    contradictory_evidence: list[TraceItem]
    assumptions: list[TraceItem]
    evidence_gaps: list[str]
    market_signals: list[TraceItem]
    customer_fit_findings: list[TraceItem]
    competitor_findings: list[TraceItem]
    commercial_risks: list[RiskItem]
    operational_risks: list[RiskItem]
    recommended_action: str
    required_changes: list[str]
    next_validation_steps: list[str]
    approval_required: bool
    provenance: OutputProvenance

    @field_validator("skill_id")
    @classmethod
    def skill_id_must_match(cls, value: str) -> str:
        if value != "ms.skill.market_validation":
            raise ValueError("skill_id must be ms.skill.market_validation")
        return value


class EvidenceItem(BaseModel):
    evidence_class: str
    summary: str
    source_ref: str | None = None
    confidence: str | None = None
    is_assumption: bool = False


class MarketValidationInputFixture(BaseModel):
    idea_description: str = Field(min_length=8)
    product_or_service: str | None = None
    target_market: str | None = None
    geography: str | None = None
    intended_customer: str | None = None
    business_model: str | None = None
    pricing_assumptions: Any | None = None
    available_budget: Any | None = None
    launch_timeline: Any | None = None
    founder_constraints: str | None = None
    known_competitors: list[str] | None = None
    available_evidence: list[EvidenceItem] | None = None
    user_risk_tolerance: str | None = None
    field_states: dict[str, str] | None = None


def load_json_fixture(relative_path: str) -> Any:
    path = PACKAGE_ROOT / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def read_manifest_text(path: Path | None = None) -> str:
    manifest_path = path or (PACKAGE_ROOT / "manifest.yaml")
    return manifest_path.read_text(encoding="utf-8")


def parse_manifest_scalar(text: str, key: str) -> str | None:
    pattern = rf"^{re.escape(key)}:\s*(.+?)\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if value.startswith('"') or value.startswith("'"):
        return value.strip("\"'")
    return value


def manifest_contains_required_keys(text: str) -> list[str]:
    missing = [key for key in REQUIRED_MANIFEST_KEYS if f"{key}:" not in text]
    return missing


def package_structure_valid(root: Path | None = None) -> bool:
    base = root or PACKAGE_ROOT
    return all((base / entry).exists() for entry in REQUIRED_PACKAGE_ENTRIES)


def package_paths_safe(root: Path | None = None) -> bool:
    base = root or PACKAGE_ROOT
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        if ".." in rel or rel.startswith("/"):
            return False
    return True


def scripts_disabled(manifest_text: str) -> bool:
    if "script_policy:" not in manifest_text:
        return False
    return "enabled: false" in manifest_text


def no_secrets_in_manifest(manifest_text: str) -> bool:
    return FORBIDDEN_SECRET_PATTERNS.search(manifest_text) is None


def validate_output_fixture(data: dict[str, Any]) -> MarketValidationOutputFixture:
    return MarketValidationOutputFixture.model_validate(data)


def validate_input_fixture(data: dict[str, Any]) -> MarketValidationInputFixture:
    return MarketValidationInputFixture.model_validate(data)


def validate_output_or_raise(data: dict[str, Any]) -> None:
    validate_output_fixture(data)


def validate_input_or_raise(data: dict[str, Any]) -> None:
    validate_input_fixture(data)


__all__ = [
    "ALLOWED_PACKAGE_STATUSES",
    "FORBIDDEN_SECRET_PATTERNS",
    "MarketValidationInputFixture",
    "MarketValidationOutputFixture",
    "MarketValidationVerdict",
    "PACKAGE_ROOT",
    "REQUIRED_MANIFEST_KEYS",
    "SKILL_01_0_ALLOWED_STATUSES",
    "load_json_fixture",
    "manifest_contains_required_keys",
    "no_secrets_in_manifest",
    "package_paths_safe",
    "package_structure_valid",
    "parse_manifest_scalar",
    "read_manifest_text",
    "scripts_disabled",
    "validate_input_fixture",
    "validate_input_or_raise",
    "validate_output_fixture",
    "validate_output_or_raise",
]
