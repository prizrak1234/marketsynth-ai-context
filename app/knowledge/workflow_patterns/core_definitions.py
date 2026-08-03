"""KB-WPL-01.3B core pattern definitions — twelve new reviewed patterns."""

from __future__ import annotations

from typing import Any

from app.knowledge.workflow_patterns.core_practice_definitions import CORE_PATTERN_PRACTICE_IDS
from app.knowledge.workflow_patterns.pattern_common import (
    base_core_pattern,
    core_edge,
    core_step,
    core_variant,
)

_APPROVAL = {
    "human_approval_required": False,
    "approval_gates": [],
    "auto_approval_allowed": False,
    "spend_approval_required": False,
    "publication_approval_required": False,
}
_IDEM = {
    "required": True,
    "policy": "dedupe_by_event_id",
    "unknown_outcome_auto_retry": False,
    "duplicate_event_prevention": True,
}
_EVIDENCE = {"required": True, "evidence_classes": ["execution_log"]}


def core_patterns() -> list[dict[str, Any]]:
    builders = (
        _pagination_and_batching,
        _checkpoint_and_resume,
        _dead_letter_queue,
        _provider_rate_limit_handling,
        _quality_gate_after_generation,
        _specialist_subworkflow,
        _supervisor_pattern,
        _tool_workflow_separation,
        _human_edit_then_resume,
        _publication_confirmation,
        _source_lineage_preservation,
        _customer_feedback_to_learning_candidate,
    )
    return [builder() for builder in builders]


def _pagination_and_batching() -> dict[str, Any]:
    pid = "pagination_and_batching"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Pagination and Batching",
        pattern_category="data_flow",
        objective="Process large datasets via bounded pages and batches.",
        problem_context="Lead retargeting and scheduled enrichment over many records.",
        capability_ids=["scheduling", "lead_generation"],
        source_workflow_ids=["wf-860ed73d41feb4fd", "wf-4795f50628f182d5"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Init cursor", "transform", "read_only"),
            core_step("s2", "Fetch page", "read", "read_only"),
            core_step("s3", "Process batch", "transform", "read_only"),
            core_step("s4", "Check termination", "branch", "read_only"),
        ],
        edges=[
            core_edge("e1", "s1", "s2"),
            core_edge("e2", "s2", "s3"),
            core_edge("e3", "s3", "s4"),
            core_edge("e4", "s4", "s2", condition="has_more"),
            core_edge("e5", "s4", "s1", condition="complete"),
        ],
        security_class="read_only",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements=_APPROVAL,
        evidence_requirements=_EVIDENCE,
        idempotency_requirements=_IDEM,
        retry_policy="backoff",
        error_paths=["human_review", "dead_letter"],
        known_limitations=[
            "max_batch_size and max_pages must be configured per tenant.",
            "Termination inferred from catalog splitInBatches metadata.",
        ],
        implementation_variants=[core_variant("Google Sheets", "storage_provider")],
        input_contract={
            "type": "object",
            "required": ["tenant_context", "correlation_id", "max_batch_size"],
        },
    )


def _checkpoint_and_resume() -> dict[str, Any]:
    pid = "checkpoint_and_resume"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Checkpoint and Resume",
        pattern_category="reliability",
        objective="Persist progress before expensive steps and resume safely.",
        problem_context="Media conversion and automation loops with wait segments.",
        capability_ids=["scheduling"],
        source_workflow_ids=["wf-6114836577421bab", "wf-6d6ba3d5c2233d5f"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Load checkpoint", "read", "read_only"),
            core_step("s2", "Write checkpoint", "write", "write_internal"),
            core_step("s3", "Expensive operation", "transform", "elevated_review"),
            core_step("s4", "Mark complete", "write", "write_internal"),
        ],
        edges=[
            core_edge("e1", "s1", "s2"),
            core_edge("e2", "s2", "s3"),
            core_edge("e3", "s3", "s4", condition="success"),
            core_edge("e4", "s3", "s1", condition="retry_from_checkpoint", on_failure="retry"),
        ],
        security_class="write_internal",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements=_APPROVAL,
        evidence_requirements={
            "required": True,
            "evidence_classes": ["execution_log", "source_reference"],
        },
        idempotency_requirements=_IDEM,
        retry_policy="bounded_backoff",
        error_paths=["human_review", "dead_letter"],
        known_limitations=["Checkpoint store format not standardized across providers."],
        implementation_variants=[core_variant("storage_provider", "checkpoint_store")],
        input_contract={
            "type": "object",
            "required": ["tenant_context", "correlation_id", "checkpoint_id"],
        },
        output_contract={
            "type": "object",
            "required": ["status", "checkpoint_id", "evidence_refs"],
        },
    )


def _dead_letter_queue() -> dict[str, Any]:
    pid = "dead_letter_queue"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Dead Letter Queue",
        pattern_category="reliability",
        objective="Route terminal failures to auditable dead-letter storage.",
        problem_context="Email dispatch and support workflows after retry exhaustion.",
        capability_ids=["customer_support", "email_marketing"],
        source_workflow_ids=["wf-4e833d762f583631", "wf-7227ff0544f5cbd2"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Classify failure", "branch", "read_only"),
            core_step("s2", "Write dead_letter_queue", "write", "write_internal"),
            core_step("s3", "Notify operator", "notify", "publication"),
        ],
        edges=[
            core_edge("e1", "s1", "s2", condition="terminal_failure"),
            core_edge("e2", "s2", "s3"),
        ],
        security_class="write_internal",
        publication_sensitive=True,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            **_APPROVAL,
            "human_approval_required": True,
            "approval_gates": ["before_publication"],
            "publication_approval_required": True,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["execution_log", "approval_record"],
        },
        idempotency_requirements=_IDEM,
        retry_policy="none",
        error_paths=["dead_letter", "human_review"],
        known_limitations=["Dead-letter retention policy is tenant-specific."],
        implementation_variants=[core_variant("Gmail", "message_channel")],
    )


def _provider_rate_limit_handling() -> dict[str, Any]:
    pid = "provider_rate_limit_handling"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Provider Rate Limit Handling",
        pattern_category="reliability",
        objective="Handle provider rate limits with safe backoff.",
        problem_context="HTTP-heavy automation and creative agent pipelines.",
        capability_ids=["agent_orchestration"],
        source_workflow_ids=["wf-6114836577421bab", "wf-b537693ad1b8ee7e"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Invoke transport", "transport", "read_only"),
            core_step("s2", "Detect rate limit", "branch", "read_only"),
            core_step("s3", "Backoff retry", "retry", "read_only"),
        ],
        edges=[
            core_edge("e1", "s1", "s2"),
            core_edge("e2", "s2", "s3", condition="rate_limited"),
            core_edge("e3", "s3", "s1", condition="retry_allowed"),
        ],
        security_class="read_only",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements=_APPROVAL,
        evidence_requirements=_EVIDENCE,
        idempotency_requirements=_IDEM,
        retry_policy="bounded_backoff",
        rate_limit_policy="exponential_backoff_with_jitter",
        error_paths=["circuit_break", "human_review"],
        known_limitations=["Retry-After headers belong in implementation_variants only."],
        implementation_variants=[core_variant("HTTP", "transport")],
    )


def _quality_gate_after_generation() -> dict[str, Any]:
    pid = "quality_gate_after_generation"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Quality Gate After Generation",
        pattern_category="ai_integration",
        objective="Block invalid LLM output before downstream handoff.",
        problem_context="SEO and credit verification agents with structured parsers.",
        capability_ids=["agent_orchestration", "seo"],
        source_workflow_ids=["wf-63b78819a2e5a190", "wf-16a4bd5f71833d44"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Generate", "generate", "read_only"),
            core_step("s2", "Validate schema", "validate", "read_only"),
            core_step("s3", "Handoff or block", "branch", "read_only"),
        ],
        edges=[
            core_edge("e1", "s1", "s2"),
            core_edge("e2", "s2", "s3", condition="valid"),
            core_edge("e3", "s2", "s1", condition="invalid", on_failure="human_review"),
        ],
        security_class="elevated_review",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements=_APPROVAL,
        evidence_requirements={
            "required": True,
            "evidence_classes": ["execution_log", "test_result"],
        },
        idempotency_requirements=_IDEM,
        retry_policy="none",
        error_paths=["human_review", "dead_letter"],
        known_limitations=["Schema validation rules are core-level; provider shapes vary."],
        implementation_variants=[core_variant("OpenAI", "LLM_provider")],
    )


def _specialist_subworkflow() -> dict[str, Any]:
    pid = "specialist_subworkflow"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Specialist Subworkflow",
        pattern_category="ai_integration",
        objective="Isolate specialist logic in bounded sub-workflow scope.",
        problem_context="Multi-tool marketing agents with document integrations.",
        capability_ids=["agent_orchestration", "publication"],
        source_workflow_ids=["wf-b2aea5e382059f4b", "wf-7c284d78aad2003d"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Declare scope", "transform", "read_only"),
            core_step("s2", "Invoke specialist", "delegate", "write_internal"),
            core_step("s3", "Validate scope", "validate", "read_only"),
        ],
        edges=[core_edge("e1", "s1", "s2"), core_edge("e2", "s2", "s3")],
        security_class="write_internal",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements=_APPROVAL,
        evidence_requirements=_EVIDENCE,
        idempotency_requirements=_IDEM,
        retry_policy="none",
        error_paths=["human_review"],
        known_limitations=["Scope declaration format not yet platform-adapted."],
        implementation_variants=[core_variant("LangChain", "agent_orchestration")],
        input_contract={
            "type": "object",
            "required": ["tenant_context", "correlation_id", "specialist_scope"],
        },
    )


def _supervisor_pattern() -> dict[str, Any]:
    pid = "supervisor_pattern"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Supervisor Pattern",
        pattern_category="ai_integration",
        objective="Supervisor orchestrates specialists without undeclared tools.",
        problem_context="IP monitoring and data privacy governance agents.",
        capability_ids=["agent_orchestration", "human_approval"],
        source_workflow_ids=["wf-6bcda126561b5f72", "wf-cb28929d37f1ac61"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Supervisor plan", "orchestrate", "read_only"),
            core_step("s2", "Delegate specialist", "delegate", "write_internal"),
            core_step("s3", "Aggregate results", "transform", "read_only"),
        ],
        edges=[core_edge("e1", "s1", "s2"), core_edge("e2", "s2", "s3")],
        security_class="elevated_review",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            **_APPROVAL,
            "human_approval_required": True,
            "approval_gates": ["before_external_action"],
        },
        evidence_requirements=_EVIDENCE,
        idempotency_requirements=_IDEM,
        retry_policy="none",
        error_paths=["human_review"],
        known_limitations=[
            "Supervisor cannot bypass tool allowlists.",
            "Undeclared tool execution forbidden at pattern level.",
        ],
        implementation_variants=[core_variant("OpenAI", "LLM_provider")],
    )


def _tool_workflow_separation() -> dict[str, Any]:
    pid = "tool_workflow_separation"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Tool Workflow Separation",
        pattern_category="ai_integration",
        objective="Separate agent tools into isolated workflows with permission boundary.",
        problem_context="Agents using message and document tools as sub-workflows.",
        capability_ids=["agent_orchestration"],
        source_workflow_ids=["wf-7c284d78aad2003d", "wf-b2aea5e382059f4b"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Tool invocation", "trigger", "read_only"),
            core_step("s2", "Enforce allowlist", "validate", "elevated_review"),
            core_step("s3", "Minimal action", "transport", "write_internal"),
        ],
        edges=[
            core_edge("e1", "s1", "s2"),
            core_edge("e2", "s2", "s3", condition="allowed"),
            core_edge("e3", "s2", "s1", condition="denied", on_failure="human_review"),
        ],
        security_class="elevated_review",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements=_APPROVAL,
        evidence_requirements=_EVIDENCE,
        idempotency_requirements=_IDEM,
        retry_policy="none",
        error_paths=["human_review", "dead_letter"],
        known_limitations=["Tool permission matrix deferred to Connector Gateway."],
        implementation_variants=[core_variant("Gmail", "message_channel")],
    )


def _human_edit_then_resume() -> dict[str, Any]:
    pid = "human_edit_then_resume"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Human Edit Then Resume",
        pattern_category="control_and_safety",
        objective="Allow human edit of draft before workflow resumes.",
        problem_context="Support email agents and legal policy governance.",
        capability_ids=["human_approval", "customer_support"],
        source_workflow_ids=["wf-7227ff0544f5cbd2", "wf-c18641f0b4421b0a"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Produce draft", "generate", "read_only"),
            core_step("s2", "Human edit gate", "approval", "elevated_review"),
            core_step("s3", "Resume branch", "branch", "read_only"),
            core_step("s4", "Persist lineage", "evidence", "write_internal"),
        ],
        edges=[
            core_edge("e1", "s1", "s2"),
            core_edge("e2", "s2", "s3"),
            core_edge("e3", "s3", "s4", condition="edit_complete"),
        ],
        security_class="elevated_review",
        publication_sensitive=True,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            "human_approval_required": True,
            "approval_gates": ["before_external_action", "before_publication"],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": True,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["approval_record", "execution_log"],
            "minimum_evidence_count": 2,
        },
        idempotency_requirements=_IDEM,
        retry_policy="none",
        error_paths=["human_review"],
        known_limitations=["Edit interface variants not standardized."],
        implementation_variants=[core_variant("Gmail", "approval_interface")],
    )


def _publication_confirmation() -> dict[str, Any]:
    pid = "publication_confirmation"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Publication Confirmation",
        pattern_category="control_and_safety",
        objective="Confirm publication succeeded and capture evidence.",
        problem_context="Quotation PDF email and social publication workflows.",
        capability_ids=["publication", "email_marketing"],
        source_workflow_ids=["wf-497aa9eee8a759da", "wf-9f3a78220a7bfbe3"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Approve draft", "approval", "publication"),
            core_step("s2", "Publish", "publish", "publication"),
            core_step("s3", "Capture confirmation", "evidence", "write_internal"),
        ],
        edges=[
            core_edge("e1", "s1", "s2", condition="approved"),
            core_edge("e2", "s2", "s3"),
        ],
        security_class="publication",
        publication_sensitive=True,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            "human_approval_required": True,
            "approval_gates": ["before_publication"],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": True,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["approval_record", "execution_log"],
            "minimum_evidence_count": 2,
        },
        idempotency_requirements=_IDEM,
        retry_policy="none",
        error_paths=["human_review", "dead_letter"],
        known_limitations=["Channel-specific confirmation payloads in variants only."],
        implementation_variants=[core_variant("Gmail", "publication_target")],
    )


def _source_lineage_preservation() -> dict[str, Any]:
    pid = "source_lineage_preservation"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Source Lineage Preservation",
        pattern_category="data_flow",
        objective="Preserve source references through transforms to output.",
        problem_context="SEO research and multi-channel content repurposing pipelines.",
        capability_ids=["seo", "agent_orchestration"],
        source_workflow_ids=["wf-63b78819a2e5a190", "wf-b2aea5e382059f4b"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Ingest source", "read", "read_only"),
            core_step("s2", "Transform with lineage", "transform", "read_only"),
            core_step("s3", "Emit lineage output", "evidence", "write_internal"),
        ],
        edges=[core_edge("e1", "s1", "s2"), core_edge("e2", "s2", "s3")],
        security_class="read_only",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements=_APPROVAL,
        evidence_requirements={
            "required": True,
            "evidence_classes": ["source_reference", "execution_log"],
            "minimum_evidence_count": 1,
        },
        idempotency_requirements={**_IDEM, "policy": "dedupe_by_content_hash"},
        retry_policy="none",
        error_paths=["human_review"],
        known_limitations=["Lineage chain format is core abstraction only."],
        implementation_variants=[core_variant("Google Docs", "storage_provider")],
        output_contract={
            "type": "object",
            "required": ["status", "source_lineage", "evidence_refs"],
        },
    )


def _customer_feedback_to_learning_candidate() -> dict[str, Any]:
    pid = "customer_feedback_to_learning_candidate"
    return base_core_pattern(
        pattern_id=pid,
        pattern_name="Customer Feedback to Learning Candidate",
        pattern_category="marketing_learning",
        objective="Convert feedback into tenant-scoped knowledge_candidate draft only.",
        problem_context="Support interactions and savings nudge feedback loops.",
        capability_ids=["customer_support", "agent_orchestration"],
        source_workflow_ids=["wf-7227ff0544f5cbd2", "wf-770099f8fbf34352"],
        source_practice_ids=CORE_PATTERN_PRACTICE_IDS[pid],
        steps=[
            core_step("s1", "Capture feedback", "trigger", "elevated_review"),
            core_step("s2", "Normalize evidence", "transform", "read_only"),
            core_step("s3", "Build candidate", "write", "write_internal"),
            core_step("s4", "Queue owner review", "approval", "elevated_review"),
        ],
        edges=[
            core_edge("e1", "s1", "s2"),
            core_edge("e2", "s2", "s3"),
            core_edge("e3", "s3", "s4"),
        ],
        security_class="elevated_review",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            "human_approval_required": True,
            "approval_gates": ["before_write"],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": False,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["source_reference", "user_statement", "execution_log"],
        },
        idempotency_requirements=_IDEM,
        retry_policy="none",
        error_paths=["human_review", "abstain"],
        known_limitations=[
            "Does not modify canonical Knowledge Core or CIM.",
            "Does not auto-promote findings or cross tenants.",
            "owner_review_required on all knowledge_candidate outputs.",
        ],
        implementation_variants=[core_variant("Google Sheets", "storage_provider")],
        input_contract={
            "type": "object",
            "required": ["tenant_context", "correlation_id", "project_context"],
        },
        output_contract={
            "type": "object",
            "required": [
                "knowledge_candidate",
                "source_evidence",
                "confidence",
                "contradictions",
                "tenant_context",
                "owner_review_required",
            ],
        },
    )
