"""Canonical Profession → Capability → Skill → Pattern → Connector → Tool contracts."""

from __future__ import annotations

CANONICAL_HIERARCHY = (
    "Profession",
    "Capability",
    "Skill",
    "Workflow Pattern",
    "Connector",
    "Tool",
)

BUNDLE_VERSION = "0.1.0"
CANONICAL_URI_BASE = "https://schemas.marketsynth.ai/capability-model/0.1.0/"
BUNDLE_STATUS = "mapped_read_only_model"
OWNER_DECISION = "accepted_as_architectural_mapping"

PROFESSION_DOMAINS = frozenset(
    {
        "marketing",
        "automation_engineering",
        "knowledge_management",
        "content_and_deliverables",
        "sales",
        "legal",
        "hr",
        "finance",
        "operations",
        "custom",
    }
)

PROFESSION_PRODUCTION_STATUSES = frozenset(
    {
        "conceptual",
        "mapped",
        "partially_implemented",
        "implemented_non_executable",
        "deferred",
        "rejected",
    }
)

CAPABILITY_IMPLEMENTATION_STATUSES = frozenset(
    {
        "specified",
        "partially_implemented",
        "implemented_non_executable",
        "blocked",
        "deferred",
        "rejected",
    }
)

CAPABILITY_READINESS_VALUES = frozenset(
    {
        "available_as_knowledge",
        "package_contract_ready",
        "runtime_not_available",
        "connector_not_available",
        "approval_boundary_missing",
        "insufficient_evidence",
        "blocked",
        "deferred",
    }
)

GAP_TYPES = frozenset(
    {
        "missing_skill",
        "missing_pattern",
        "missing_connector",
        "missing_tool",
        "missing_runtime",
        "missing_approval",
        "missing_evidence",
        "missing_contract",
        "version_incompatibility",
        "capability_not_released",
        "unknown",
    }
)

CONNECTOR_CLASSES = frozenset(
    {
        "research_connector",
        "analytics_connector",
        "content_generation_connector",
        "rendering_connector",
        "publication_connector",
        "CRM_connector",
        "advertising_connector",
        "storage_connector",
        "development_connector",
        "collaboration_connector",
    }
)

TOOL_CLASSES = frozenset(
    {
        "read",
        "search",
        "analyze",
        "generate_draft",
        "render",
        "write",
        "publish",
        "delete",
        "administer",
        "spend",
    }
)

PROFESSION_IDS = frozenset(
    {
        "profession.ai_marketing_director",
        "profession.automation_architect",
        "profession.knowledge_architect",
        "profession.content_deliverables_architect",
    }
)

FORBIDDEN_RUNTIME_FIELDS = frozenset(
    {
        "runtime_authorized",
        "execution_status",
        "connector_activated",
        "tool_allowlist_granted",
        "skill_activated",
        "orchestration_enabled",
        "autonomous_agent",
        "employee_runtime",
        "telegram_mcp",
        "permission_granted",
        "production_eligible",
    }
)

FORBIDDEN_ORCHESTRATION_TERMS = frozenset(
    {
        "Department",
        "Agent Type",
        "Worker",
        "Employee Runtime",
        "Role Skill Tree",
    }
)

NATIVE_TELEGRAM_BOUNDARY = (
    "Native Telegram publication remains authoritative via existing publishing "
    "foundation; no Telegram MCP introduced in this phase."
)
