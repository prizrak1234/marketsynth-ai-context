"""KB-WPL-01.8 Knowledge Discovery — contracts and enums."""

from __future__ import annotations

BUNDLE_VERSION = "0.1.0"
BUNDLE_STATUS = "read_only_discovery_model"
CANONICAL_URI_BASE = "https://schemas.marketsynth.ai/discovery/0.1.0/"

EXECUTION_SENSITIVITIES = frozenset(
    {
        "none",
        "read_only",
        "draft_generation",
        "write",
        "publication",
        "billing",
        "destructive",
        "unknown",
    }
)

QUERY_MODES = frozenset(
    {
        "task_routing",
        "capability_lookup",
        "skill_lookup",
        "workflow_pattern_lookup",
        "engineering_diagnosis_lookup",
        "knowledge_maintenance_lookup",
        "deliverable_lookup",
        "internal_audit_lookup",
    }
)

RESULT_ARTIFACT_TYPES = frozenset(
    {
        "profession",
        "capability",
        "internal_skill",
        "workflow_pattern",
        "practice_record",
        "error_pattern",
        "knowledge_artifact",
        "capability_gap",
        "connector_class",
        "tool_class",
        "quarantined_workflow_template",
        "rejected_artifact_reference",
    }
)

CUSTOMER_FACING_TYPES = frozenset(
    {
        "profession",
        "capability",
        "internal_skill",
        "workflow_pattern",
        "capability_gap",
        "connector_class",
        "tool_class",
    }
)

AUDIT_ONLY_TYPES = frozenset(
    {
        "practice_record",
        "error_pattern",
        "quarantined_workflow_template",
        "rejected_artifact_reference",
    }
)

MATCH_TYPES = frozenset(
    {
        "exact_id",
        "exact_title",
        "exact_token",
        "alias",
        "declared_binding",
        "dependency",
        "provider_constraint",
        "platform_constraint",
        "error_symptom",
        "gap_relation",
        "supporting_practice",
        "other",
    }
)

CONFIDENCE_LEVELS = frozenset({"high", "medium", "low", "unknown"})

SAFE_NEXT_ACTIONS = frozenset(
    {
        "use_internal_skill_contract",
        "review_workflow_pattern",
        "review_practice",
        "inspect_error_pattern",
        "gather_missing_evidence",
        "request_human_review",
        "request_security_review",
        "request_connector_design",
        "request_runtime_implementation",
        "adapt_internal_methodology",
        "defer",
        "reject",
    }
)

FORBIDDEN_RECOMMENDED_ACTIONS = frozenset(
    {
        "install_skill",
        "activate_skill",
        "execute_skill",
        "deploy_workflow",
        "activate_connector",
        "grant_permission",
        "publish",
        "spend",
    }
)

SECRET_PATTERNS = (
    "api_key",
    "apikey",
    "password",
    "oauth",
    "bearer ",
    "private_key",
    "secret",
    "credential",
    "sk-",
    "-----begin",
)

MAX_RESULT_LIMIT = 50
DEFAULT_RESULT_LIMIT = 10
