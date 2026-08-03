"""Frozen knowledge references for n8n Engineering Skills."""

from __future__ import annotations

FROZEN_LIBRARY_SEMANTIC_HASH = (
    "1ddd0d033f6028bd5dcf5ee555186c6be0389a96459615b6221348783d9b1883"
)
FROZEN_CATALOG_HASH = "5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa"
LIBRARY_VERSION = "0.1.0-frozen"

N8N_ENGINEERING_SKILL_IDS = (
    "ms.skill.n8n_workflow_architecture",
    "ms.skill.n8n_workflow_debugging",
    "ms.skill.n8n_deployment_review",
)

KNOWN_PATTERN_IDS = frozenset(
    {
        "human_approval_before_publication",
        "structured_LLM_to_API_request",
        "retry_with_idempotency",
        "evidence_grounded_generation",
        "lead_capture_to_qualification",
        "draft_to_human_approval",
        "workflow_backup",
        "error_workflow_or_recovery",
        "pagination_and_batching",
        "checkpoint_and_resume",
        "dead_letter_queue",
        "provider_rate_limit_handling",
        "quality_gate_after_generation",
        "specialist_subworkflow",
        "supervisor_pattern",
        "tool_workflow_separation",
        "human_edit_then_resume",
        "publication_confirmation",
        "source_lineage_preservation",
        "customer_feedback_to_learning_candidate",
    }
)

PROHIBITED_MATURITY = frozenset(
    {
        "active",
        "executable",
        "deployed",
        "approved",
        "platform_adapted",
        "production_ready",
    }
)

DEBUG_ERROR_CLASSES = frozenset(
    {
        "input_contract_error",
        "output_contract_error",
        "expression_error",
        "type_mismatch",
        "missing_field",
        "credential_reference_error",
        "provider_auth_error",
        "provider_rate_limit",
        "provider_timeout",
        "webhook_error",
        "trigger_error",
        "database_error",
        "messaging_payload_error",
        "duplicate_event",
        "idempotency_error",
        "unknown_outcome",
        "AI_tool_boundary_error",
        "structured_output_error",
        "prompt_injection_risk",
        "code_node_error",
        "version_compatibility_error",
        "activation_or_settings_error",
        "unknown",
    }
)
