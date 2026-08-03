"""Workflow catalog contracts — KB-WPL-01.2 (immutable, metadata-only)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AdaptationStatus = Literal[
    "catalog_only",
    "reusable_pattern_candidate",
    "requires_rewrite",
    "rejected",
    "deferred",
    "superseded",
]
QuarantineStatus = Literal["quarantined", "reviewed", "rejected"]
PersonalDataRisk = Literal["none", "low", "elevated", "high", "unknown"]
CommercialPriority = Literal[
    "P0_core_marketing",
    "P1_content_distribution_analytics",
    "P2_platform_extensions",
    "engineering_reference",
    "catalog_only",
    "reject",
]
DuplicateFamilyType = Literal[
    "exact_duplicate",
    "renamed_topology",
    "translated_duplicate",
    "provider_swapped",
    "version_variant",
    "credential_only_variant",
    "sample_content_variant",
    "probable_supersession",
]

SOURCE_ARCHIVE_ID = "arc-bots-knowledge-rar"


class SecurityFindingRecord(BaseModel):
    finding_id: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    finding_type: str
    location: str
    description: str
    redacted: bool = True
    provenance: dict[str, Any]

    model_config = {"extra": "forbid", "frozen": True}


class CredentialReference(BaseModel):
    credential_type: str
    credential_id_ref: str
    node_name: str = ""

    model_config = {"extra": "forbid", "frozen": True}


class WorkflowTemplateRecord(BaseModel):
    workflow_template_id: str
    original_name: str
    normalized_name: str
    source_archive_id: str
    source_path_hash: str = Field(min_length=64, max_length=64)
    workflow_hash: str = Field(min_length=64, max_length=64)
    topology_hash: str = Field(min_length=64, max_length=64)
    description: str = ""
    use_case: str = ""
    categories: list[str] = Field(default_factory=list)
    trigger_types: list[str] = Field(default_factory=list)
    node_types: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    credential_references: list[CredentialReference] = Field(default_factory=list)
    environment_references: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    publication_actions: bool = False
    billing_actions: bool = False
    destructive_actions: bool = False
    personal_data_risk: PersonalDataRisk = "unknown"
    code_nodes: bool = False
    shell_nodes: bool = False
    database_nodes: bool = False
    AI_nodes: bool = False
    external_urls: list[str] = Field(default_factory=list)
    security_findings: list[SecurityFindingRecord] = Field(default_factory=list)
    provider_constraints: list[dict[str, Any]] = Field(default_factory=list)
    deprecated_components: list[str] = Field(default_factory=list)
    adaptation_status: AdaptationStatus = "catalog_only"
    quarantine_status: QuarantineStatus = "quarantined"
    tenant_scope: str = "global"
    provenance: dict[str, Any]

    model_config = {"extra": "forbid", "frozen": True}


class DuplicateFamily(BaseModel):
    family_id: str
    family_type: DuplicateFamilyType
    member_workflow_ids: list[str]
    canonical_candidate_id: str
    differences: list[str] = Field(default_factory=list)
    confidence: str
    manual_review_required: bool = True
    provenance: dict[str, Any]

    model_config = {"extra": "forbid", "frozen": True}


class InvalidFileRecord(BaseModel):
    file_name: str
    source_path_hash: str
    reason: str
    error_type: str

    model_config = {"extra": "forbid", "frozen": True}


class WorkflowCatalogBundle(BaseModel):
    schema_version: str
    schema_bundle_ref: str
    generated_at: str
    source_archive_id: str
    json_discovered: int
    valid_exports: int
    invalid_count: int
    templates: list[WorkflowTemplateRecord]
    invalid_files: list[InvalidFileRecord] = Field(default_factory=list)

    model_config = {"extra": "forbid", "frozen": True}
