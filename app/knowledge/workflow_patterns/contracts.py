"""Workflow pattern pilot contracts — immutable read models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PilotMaturity = Literal["reviewed"]
AuditDecision = Literal["approved_for_pilot", "approved_for_core", "deferred", "rejected"]


class ManualAuditRecord(BaseModel):
    audit_id: str
    workflow_template_ids: list[str]
    pattern_ids: list[str]
    decision: AuditDecision
    rationale: str
    limitations: list[str] = Field(default_factory=list)
    program_phase: str = "KB-WPL-01.3A.1"
    reviewer_role: str = "architecture_reviewer_agent"
    review_method: str = "catalog_metadata_crosswalk"
    reviewed_source_ids: list[str] = Field(default_factory=list)
    reviewed_practice_ids: list[str] = Field(default_factory=list)
    review_timestamp: str = ""
    audit_hash: str = ""
    owner_review_required: bool = True
    reviewer: str | None = None

    model_config = {"extra": "forbid", "frozen": True}


class SourceSupportResult(BaseModel):
    supported: bool
    support_mode: Literal["two_source", "single_source_audited", "unsupported"]
    reasons: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid", "frozen": True}


class PatternValidationReport(BaseModel):
    pattern_id: str
    schema_valid: bool
    semantic_errors: list[str] = Field(default_factory=list)
    quality_gate_errors: list[str] = Field(default_factory=list)
    source_support: SourceSupportResult | None = None

    model_config = {"extra": "forbid", "frozen": True}


SINGLE_SOURCE_POLICY: dict[str, Any] = {
    "policy_id": "wpl-single-source-01.3b",
    "program_phase": "KB-WPL-01.3A.1",
    "allowed_when": [
        "one valid catalog workflow exists",
        "at least one real PracticeRecord supports the architecture",
        "explicit manual audit is present",
        "source-support map is complete",
        "limitations are explicit",
        "maturity remains reviewed",
        "owner or delegated architecture reviewer signs the audit record",
    ],
    "forbidden_when": [
        "zero source workflows",
        "placeholder practice lineage",
        "incomplete source-support map",
        "owner_review_required=false without signed owner audit",
    ],
    "owner_review_required_default": True,
}

PilotPatternDict = dict[str, Any]
