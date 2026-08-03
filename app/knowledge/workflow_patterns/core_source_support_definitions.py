"""KB-WPL-01.3B core source-support map."""

from __future__ import annotations

from typing import Any

from app.knowledge.workflow_patterns.core_practice_definitions import CORE_PATTERN_PRACTICE_IDS
from app.knowledge.workflow_patterns.source_support_definitions import _signal


def _entry(
    pattern_id: str,
    source_workflow_ids: list[str],
    signals: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "pattern_id": pattern_id,
        "source_workflow_ids": source_workflow_ids,
        "source_practice_ids": CORE_PATTERN_PRACTICE_IDS[pattern_id],
        "manual_audit_id": f"audit-core-{pattern_id}",
        "supporting_signals": signals,
    }


def core_source_support_map() -> dict[str, Any]:
    entries = [
        _entry(
            "pagination_and_batching",
            ["wf-860ed73d41feb4fd", "wf-4795f50628f182d5"],
            [
                _signal(
                    source_workflow_id="wf-860ed73d41feb4fd",
                    signal_type="branch_structure",
                    node_or_functional_class="n8n-nodes-base.splitInBatches",
                    topology_location="retargeting_batch_loop",
                    supported_pattern_rule="bounded_batch_processing",
                    confidence="explicit",
                    limitations=["WhatsApp retargeting domain-specific variant."],
                ),
                _signal(
                    source_workflow_id="wf-4795f50628f182d5",
                    signal_type="trigger_structure",
                    node_or_functional_class="n8n-nodes-base.scheduleTrigger",
                    topology_location="scheduled_batch_entry",
                    supported_pattern_rule="pagination_until_exhausted",
                    confidence="probable",
                    limitations=["Schedule filter batch inferred from metadata."],
                ),
            ],
        ),
        _entry(
            "checkpoint_and_resume",
            ["wf-6114836577421bab", "wf-6d6ba3d5c2233d5f"],
            [
                _signal(
                    source_workflow_id="wf-6114836577421bab",
                    signal_type="retry_structure",
                    node_or_functional_class="n8n-nodes-base.wait",
                    topology_location="music_automation_wait_segment",
                    supported_pattern_rule="checkpoint_before_expensive_step",
                    confidence="probable",
                    limitations=["Also supports rate_limit pattern via httpRequest."],
                ),
                _signal(
                    source_workflow_id="wf-6d6ba3d5c2233d5f",
                    signal_type="recovery_action",
                    node_or_functional_class="n8n-nodes-base.wait",
                    topology_location="media_conversion_pause",
                    supported_pattern_rule="resume_from_checkpoint",
                    confidence="probable",
                    limitations=["GIF conversion wait step only."],
                ),
            ],
        ),
        _entry(
            "dead_letter_queue",
            ["wf-4e833d762f583631", "wf-7227ff0544f5cbd2"],
            [
                _signal(
                    source_workflow_id="wf-4e833d762f583631",
                    signal_type="error_path",
                    node_or_functional_class="n8n-nodes-base.httpRequest",
                    topology_location="ticket_dispatch_failure_branch",
                    supported_pattern_rule="terminal_dead_letter_handling",
                    confidence="probable",
                    limitations=["Email dispatch failure path inferred."],
                ),
                _signal(
                    source_workflow_id="wf-7227ff0544f5cbd2",
                    signal_type="human_decision",
                    node_or_functional_class="human_approval",
                    topology_location="support_escalation_terminal",
                    supported_pattern_rule="operator_notification_on_terminal_failure",
                    confidence="explicit",
                    limitations=["Also supports human_edit and feedback patterns."],
                ),
            ],
        ),
        _entry(
            "provider_rate_limit_handling",
            ["wf-6114836577421bab", "wf-b537693ad1b8ee7e"],
            [
                _signal(
                    source_workflow_id="wf-6114836577421bab",
                    signal_type="retry_structure",
                    node_or_functional_class="n8n-nodes-base.httpRequest",
                    topology_location="external_api_retry_segment",
                    supported_pattern_rule="rate_limit_backoff",
                    confidence="probable",
                    limitations=["Shared with checkpoint pattern on same workflow."],
                ),
                _signal(
                    source_workflow_id="wf-b537693ad1b8ee7e",
                    signal_type="retry_structure",
                    node_or_functional_class="n8n-nodes-base.httpRequest",
                    topology_location="creative_api_call",
                    supported_pattern_rule="bounded_retry_on_transient_failure",
                    confidence="probable",
                    limitations=["Creative agent HTTP calls only."],
                ),
            ],
        ),
        _entry(
            "quality_gate_after_generation",
            ["wf-63b78819a2e5a190", "wf-16a4bd5f71833d44"],
            [
                _signal(
                    source_workflow_id="wf-63b78819a2e5a190",
                    signal_type="structured_output",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.outputParserStructured",
                    topology_location="seo_agent_output_validation",
                    supported_pattern_rule="quality_gate_before_handoff",
                    confidence="explicit",
                    limitations=["Also supports source_lineage via aggregate nodes."],
                ),
                _signal(
                    source_workflow_id="wf-16a4bd5f71833d44",
                    signal_type="schema_validation",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.outputParserStructured",
                    topology_location="credit_verification_parser",
                    supported_pattern_rule="block_invalid_llm_output",
                    confidence="explicit",
                    limitations=["Financial domain requires elevated review."],
                ),
            ],
        ),
        _entry(
            "specialist_subworkflow",
            ["wf-b2aea5e382059f4b", "wf-7c284d78aad2003d"],
            [
                _signal(
                    source_workflow_id="wf-b2aea5e382059f4b",
                    signal_type="branch_structure",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.agent",
                    topology_location="facebook_content_specialist_chain",
                    supported_pattern_rule="specialist_scope_isolation",
                    confidence="probable",
                    limitations=["Also supports tool_workflow and lineage patterns."],
                ),
                _signal(
                    source_workflow_id="wf-7c284d78aad2003d",
                    signal_type="other",
                    node_or_functional_class="agent_orchestration",
                    topology_location="multi_tool_specialist_delegate",
                    supported_pattern_rule="specialist_subworkflow_invocation",
                    confidence="explicit",
                    limitations=["Gmail/Telegram tools as separate invocations."],
                ),
            ],
        ),
        _entry(
            "supervisor_pattern",
            ["wf-6bcda126561b5f72", "wf-cb28929d37f1ac61"],
            [
                _signal(
                    source_workflow_id="wf-6bcda126561b5f72",
                    signal_type="other",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.agentTool",
                    topology_location="ip_governance_supervisor_delegate",
                    supported_pattern_rule="supervisor_does_not_execute_tools",
                    confidence="explicit",
                    limitations=["Governance domain; marketing adaptation needs review."],
                ),
                _signal(
                    source_workflow_id="wf-cb28929d37f1ac61",
                    signal_type="approval_gate",
                    node_or_functional_class="human_approval",
                    topology_location="privacy_risk_supervisor_review",
                    supported_pattern_rule="supervisor_orchestrates_specialists",
                    confidence="explicit",
                    limitations=["PII elevated review required."],
                ),
            ],
        ),
        _entry(
            "tool_workflow_separation",
            ["wf-7c284d78aad2003d", "wf-b2aea5e382059f4b"],
            [
                _signal(
                    source_workflow_id="wf-7c284d78aad2003d",
                    signal_type="other",
                    node_or_functional_class="n8n-nodes-base.gmailTool",
                    topology_location="isolated_gmail_tool_workflow",
                    supported_pattern_rule="tool_workflow_permission_boundary",
                    confidence="explicit",
                    limitations=["Same workflow supports specialist pattern."],
                ),
                _signal(
                    source_workflow_id="wf-b2aea5e382059f4b",
                    signal_type="other",
                    node_or_functional_class="n8n-nodes-base.googleDocsTool",
                    topology_location="document_tool_subworkflow",
                    supported_pattern_rule="minimal_tool_action_only",
                    confidence="probable",
                    limitations=["Tool scope inferred from agentTool metadata."],
                ),
            ],
        ),
        _entry(
            "human_edit_then_resume",
            ["wf-7227ff0544f5cbd2", "wf-c18641f0b4421b0a"],
            [
                _signal(
                    source_workflow_id="wf-7227ff0544f5cbd2",
                    signal_type="human_decision",
                    node_or_functional_class="human_approval",
                    topology_location="support_draft_edit_gate",
                    supported_pattern_rule="manual_edit_resume",
                    confidence="explicit",
                    limitations=["Shared with feedback and dead_letter sources."],
                ),
                _signal(
                    source_workflow_id="wf-c18641f0b4421b0a",
                    signal_type="approval_gate",
                    node_or_functional_class="human_approval",
                    topology_location="legal_policy_edit_review",
                    supported_pattern_rule="resume_after_authoritative_edit",
                    confidence="explicit",
                    limitations=["Legal domain adaptation deferred."],
                ),
            ],
        ),
        _entry(
            "publication_confirmation",
            ["wf-497aa9eee8a759da", "wf-9f3a78220a7bfbe3"],
            [
                _signal(
                    source_workflow_id="wf-497aa9eee8a759da",
                    signal_type="publication_action",
                    node_or_functional_class="n8n-nodes-base.gmail",
                    topology_location="quotation_pdf_email_confirm",
                    supported_pattern_rule="post_publish_evidence_capture",
                    confidence="explicit",
                    limitations=["PDF generation step precedes send."],
                ),
                _signal(
                    source_workflow_id="wf-9f3a78220a7bfbe3",
                    signal_type="publication_action",
                    node_or_functional_class="publication",
                    topology_location="social_publish_confirm_branch",
                    supported_pattern_rule="publication_approval_required",
                    confidence="probable",
                    limitations=["HTTP publication variant."],
                ),
            ],
        ),
        _entry(
            "source_lineage_preservation",
            ["wf-63b78819a2e5a190", "wf-b2aea5e382059f4b"],
            [
                _signal(
                    source_workflow_id="wf-63b78819a2e5a190",
                    signal_type="provenance_capture",
                    node_or_functional_class="n8n-nodes-base.aggregate",
                    topology_location="seo_research_lineage_chain",
                    supported_pattern_rule="source_lineage_preservation",
                    confidence="probable",
                    limitations=["Also supports quality_gate on same workflow."],
                ),
                _signal(
                    source_workflow_id="wf-b2aea5e382059f4b",
                    signal_type="evidence_reference",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.outputParserStructured",
                    topology_location="repurpose_content_lineage",
                    supported_pattern_rule="carry_source_reference_through_transform",
                    confidence="probable",
                    limitations=["Multi-channel repurposing variant."],
                ),
            ],
        ),
        _entry(
            "customer_feedback_to_learning_candidate",
            ["wf-7227ff0544f5cbd2", "wf-770099f8fbf34352"],
            [
                _signal(
                    source_workflow_id="wf-7227ff0544f5cbd2",
                    signal_type="trigger_structure",
                    node_or_functional_class="n8n-nodes-base.gmailTrigger",
                    topology_location="support_feedback_intake",
                    supported_pattern_rule="feedback_to_knowledge_candidate",
                    confidence="probable",
                    limitations=["Customer PII requires elevated review."],
                ),
                _signal(
                    source_workflow_id="wf-770099f8fbf34352",
                    signal_type="other",
                    node_or_functional_class="agent_orchestration",
                    topology_location="nudge_feedback_capture",
                    supported_pattern_rule="knowledge_candidate_not_canonical_write",
                    confidence="probable",
                    limitations=["Personal finance domain; marketing use needs reframing."],
                ),
            ],
        ),
    ]
    return {
        "core_version": "0.1.0-core",
        "program_phase": "KB-WPL-01.3B",
        "multi_pattern_source_policy": (
            "Workflows may support multiple core patterns with pattern-specific signals."
        ),
        "entries": entries,
    }
