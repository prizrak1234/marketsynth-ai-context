"""Shared contracts for Knowledge Linking."""

from __future__ import annotations

ALLOWED_ARTIFACT_TYPES = frozenset(
    {
        "skill",
        "skill_version",
        "workflow_pattern",
        "workflow_template",
        "practice_record",
        "error_pattern",
        "knowledge_artifact",
        "schema_bundle",
        "RFC",
        "architecture_document",
        "capability",
        "profession",
        "connector",
        "tool",
        "audit_report",
        "lineage_graph",
        "evidence_reference",
        "source_archive",
        "other",
    }
)

BROKEN_LINK_FAILURE_TYPES = frozenset(
    {
        "missing_target",
        "missing_version",
        "hash_mismatch",
        "unresolved_schema",
        "stale_reference",
        "missing_lineage_parent",
        "missing_index_entry",
        "missing_manifest_entry",
        "tenant_visibility_failure",
        "invalid_relation",
        "unknown",
    }
)

DUPLICATE_TYPES = frozenset(
    {
        "exact_content",
        "identity_conflict",
        "version_conflict",
        "normalized_title",
        "topology_equivalent",
        "semantic_practice_overlap",
        "copied_source",
        "unknown",
    }
)

SUPERSESSION_COMPATIBILITY = frozenset(
    {"compatible", "conditionally_compatible", "incompatible", "unknown"}
)

CONTRADICTION_TYPES = frozenset(
    {
        "contract_conflict",
        "version_conflict",
        "lifecycle_conflict",
        "security_policy_conflict",
        "provider_behavior_conflict",
        "terminology_conflict",
        "capability_conflict",
        "hash_conflict",
        "provenance_conflict",
        "unknown",
    }
)

INDEX_TYPES = frozenset(
    {
        "domain_index",
        "skill_matrix",
        "pattern_catalog",
        "capability_binding",
        "version_index",
        "source_archive_index",
        "contradiction_index",
        "orphan_collection",
        "stale_index_entry",
    }
)

RESEARCH_STATUS = frozenset(
    {
        "complete",
        "partially_complete",
        "insufficient_sources",
        "conflicted",
        "out_of_scope",
    }
)

FORBIDDEN_OUTPUT_FIELDS = frozenset(
    {
        "links_applied",
        "files_modified",
        "records_merged",
        "records_deleted",
        "database_write",
        "graph_persisted",
        "approval_granted",
        "execution_status",
    }
)

FORBIDDEN_INPUT_FIELDS = frozenset(
    {
        "filesystem_root",
        "shell_command",
        "workflow_json",
        "api_key",
        "password",
        "credential_value",
    }
)

STANDALONE_EXEMPTION_FLAGS = frozenset(
    {
        "standalone_source_archive",
        "frozen_root_index",
        "intentionally_isolated_rejected",
    }
)

SKILL_ID = "ms.skill.knowledge_linking"
SKILL_VERSION = "0.1.0"
