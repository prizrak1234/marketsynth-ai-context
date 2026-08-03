"""KB-WPL-01.3A.1 pilot source-support map — pattern-specific structural evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.knowledge.workflow_patterns.practice_definitions import PATTERN_PRACTICE_IDS


def _evidence_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _signal(
    *,
    source_workflow_id: str,
    signal_type: str,
    node_or_functional_class: str,
    topology_location: str,
    supported_pattern_rule: str,
    confidence: str,
    limitations: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = {
        "source_workflow_id": source_workflow_id,
        "signal_type": signal_type,
        "node_or_functional_class": node_or_functional_class,
        "topology_location": topology_location,
        "supported_pattern_rule": supported_pattern_rule,
        "confidence": confidence,
        "limitations": limitations,
    }
    if extra:
        base.update(extra)
    base["evidence_hash"] = _evidence_hash(
        {
            "source_workflow_id": source_workflow_id,
            "signal_type": signal_type,
            "node_or_functional_class": node_or_functional_class,
            "topology_location": topology_location,
            "supported_pattern_rule": supported_pattern_rule,
        }
    )
    return base


def pilot_source_support_map() -> dict[str, Any]:
    """Pattern-specific support claims; workflows may appear in multiple patterns."""
    entries: list[dict[str, Any]] = [
        {
            "pattern_id": "human_approval_before_publication",
            "source_workflow_ids": ["wf-febea81827b8ad6b", "wf-16b82581942c24a9"],
            "source_practice_ids": PATTERN_PRACTICE_IDS["human_approval_before_publication"],
            "manual_audit_id": "audit-human_approval_before_publication",
            "supporting_signals": [
                _signal(
                    source_workflow_id="wf-febea81827b8ad6b",
                    signal_type="approval_gate",
                    node_or_functional_class="n8n-nodes-base.switch",
                    topology_location="pre_publication_branch_moderator",
                    supported_pattern_rule="publication_approval_required_before_publication_target",
                    confidence="probable",
                    limitations=[
                        "Switch branch semantics inferred from catalog categories, not executed.",
                    ],
                ),
                _signal(
                    source_workflow_id="wf-febea81827b8ad6b",
                    signal_type="publication_action",
                    node_or_functional_class="publication",
                    topology_location="post_approval_publish_chain",
                    supported_pattern_rule="evidence_after_publication_required",
                    confidence="probable",
                    limitations=["Publication nodes span Telegram/LinkedIn variants."],
                ),
                _signal(
                    source_workflow_id="wf-16b82581942c24a9",
                    signal_type="human_decision",
                    node_or_functional_class="human_approval",
                    topology_location="seo_publication_pipeline",
                    supported_pattern_rule="human_approval_before_write_or_publication",
                    confidence="explicit",
                    limitations=["Agent-assisted draft; human gate before Gmail publish."],
                ),
                _signal(
                    source_workflow_id="wf-16b82581942c24a9",
                    signal_type="publication_action",
                    node_or_functional_class="n8n-nodes-base.gmail",
                    topology_location="downstream_publication_target",
                    supported_pattern_rule="publication_approval_required",
                    confidence="explicit",
                    limitations=["Gmail send is publication side effect."],
                ),
            ],
        },
        {
            "pattern_id": "structured_LLM_to_API_request",
            "source_workflow_ids": ["wf-353be45a7de607a0", "wf-b6c98c93d44e4384"],
            "source_practice_ids": PATTERN_PRACTICE_IDS["structured_LLM_to_API_request"],
            "manual_audit_id": "audit-structured_LLM_to_API_request",
            "supporting_signals": [
                _signal(
                    source_workflow_id="wf-353be45a7de607a0",
                    signal_type="structured_output",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.openAi",
                    topology_location="lead_enrichment_llm_stage",
                    supported_pattern_rule="schema_validation_before_transport",
                    confidence="explicit",
                    limitations=[
                        "Shared workflow also supports lead_capture pattern via different signal.",
                    ],
                ),
                _signal(
                    source_workflow_id="wf-353be45a7de607a0",
                    signal_type="schema_validation",
                    node_or_functional_class="n8n-nodes-base.if",
                    topology_location="post_llm_validation_branch",
                    supported_pattern_rule="invalid_payload_routes_to_human_review",
                    confidence="probable",
                    limitations=["IF branch inferred from topology metadata."],
                ),
                _signal(
                    source_workflow_id="wf-b6c98c93d44e4384",
                    signal_type="structured_output",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.agent",
                    topology_location="research_agent_output_stage",
                    supported_pattern_rule="structured_output_before_API_call",
                    confidence="probable",
                    limitations=[
                        "Firecrawl tool output requires human review for high-stakes writes.",
                    ],
                ),
                _signal(
                    source_workflow_id="wf-b6c98c93d44e4384",
                    signal_type="evidence_reference",
                    node_or_functional_class="agent_orchestration",
                    topology_location="tool_retrieval_before_answer",
                    supported_pattern_rule="source_backed_research_not_raw_copy",
                    confidence="probable",
                    limitations=["Untrusted web content flagged in catalog security findings."],
                ),
            ],
        },
        {
            "pattern_id": "retry_with_idempotency",
            "source_workflow_ids": ["wf-b6e1676935a48901", "wf-60870942fc4ef5b9"],
            "source_practice_ids": PATTERN_PRACTICE_IDS["retry_with_idempotency"],
            "manual_audit_id": "audit-retry_with_idempotency",
            "supporting_signals": [
                _signal(
                    source_workflow_id="wf-b6e1676935a48901",
                    signal_type="retry_structure",
                    node_or_functional_class="n8n-nodes-base.wait",
                    topology_location="alert_retry_backoff_segment",
                    supported_pattern_rule="idempotency_before_retry",
                    confidence="probable",
                    limitations=[
                        "Shared workflow also supports error_recovery via failure branch signal.",
                    ],
                ),
                _signal(
                    source_workflow_id="wf-b6e1676935a48901",
                    signal_type="deduplication_key",
                    node_or_functional_class="n8n-nodes-base.set",
                    topology_location="pre_notification_key_assignment",
                    supported_pattern_rule="duplicate_event_prevention",
                    confidence="probable",
                    limitations=["Dedup key field names not copied from source."],
                ),
                _signal(
                    source_workflow_id="wf-60870942fc4ef5b9",
                    signal_type="retry_structure",
                    node_or_functional_class="n8n-nodes-base.if",
                    topology_location="expiry_alert_retry_branch",
                    supported_pattern_rule="bounded_retry_with_terminal_failure",
                    confidence="probable",
                    limitations=["Webhook-triggered alert path."],
                ),
                _signal(
                    source_workflow_id="wf-60870942fc4ef5b9",
                    signal_type="branch_structure",
                    node_or_functional_class="publication",
                    topology_location="notification_outcome_classifier",
                    supported_pattern_rule="unknown_outcome_write_no_auto_retry",
                    confidence="probable",
                    limitations=["Write vs read classification from side_effects metadata."],
                ),
            ],
        },
        {
            "pattern_id": "evidence_grounded_generation",
            "source_workflow_ids": ["wf-b144bd6927caa092", "wf-9c87e7783b3cb118"],
            "source_practice_ids": PATTERN_PRACTICE_IDS["evidence_grounded_generation"],
            "manual_audit_id": "audit-evidence_grounded_generation",
            "supporting_signals": [
                _signal(
                    source_workflow_id="wf-b144bd6927caa092",
                    signal_type="evidence_reference",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.outputParserStructured",
                    topology_location="ranking_agent_structured_output",
                    supported_pattern_rule="source_references_required_in_output",
                    confidence="explicit",
                    limitations=["Structured parser does not alone prove grounding quality."],
                ),
                _signal(
                    source_workflow_id="wf-b144bd6927caa092",
                    signal_type="structured_output",
                    node_or_functional_class="rag",
                    topology_location="agent_retrieval_chain",
                    supported_pattern_rule="no_source_no_grounded_claim",
                    confidence="probable",
                    limitations=["Perplexity tool adds external retrieval variant."],
                ),
                _signal(
                    source_workflow_id="wf-9c87e7783b3cb118",
                    signal_type="evidence_reference",
                    node_or_functional_class="@n8n/n8n-nodes-langchain.vectorStorePGVector",
                    topology_location="vector_retrieval_before_generate",
                    supported_pattern_rule="retrieval_provenance_before_LLM_provider",
                    confidence="explicit",
                    limitations=["Postgres vector store is implementation variant only."],
                ),
                _signal(
                    source_workflow_id="wf-9c87e7783b3cb118",
                    signal_type="other",
                    node_or_functional_class="untrusted_content_to_llm",
                    topology_location="pre_llm_injection_boundary",
                    supported_pattern_rule="prompt_injection_boundary",
                    confidence="explicit",
                    limitations=["Catalog security finding triggers elevated review."],
                ),
            ],
        },
        {
            "pattern_id": "lead_capture_to_qualification",
            "source_workflow_ids": ["wf-353be45a7de607a0", "wf-bdf26007404af6a3"],
            "source_practice_ids": PATTERN_PRACTICE_IDS["lead_capture_to_qualification"],
            "manual_audit_id": "audit-lead_capture_to_qualification",
            "supporting_signals": [
                _signal(
                    source_workflow_id="wf-353be45a7de607a0",
                    signal_type="branch_structure",
                    node_or_functional_class="n8n-nodes-base.splitInBatches",
                    topology_location="batch_lead_qualification_loop",
                    supported_pattern_rule="qualify_before_CRM_write",
                    confidence="explicit",
                    limitations=[
                        "Same workflow supports structured_LLM via openAi node signal, "
                        "not this branch.",
                    ],
                ),
                _signal(
                    source_workflow_id="wf-353be45a7de607a0",
                    signal_type="trigger_structure",
                    node_or_functional_class="n8n-nodes-base.googleDriveTrigger",
                    topology_location="inbound_lead_capture_entry",
                    supported_pattern_rule="lead_capture_to_qualification_entry",
                    confidence="explicit",
                    limitations=["Drive trigger is capture variant only."],
                ),
                _signal(
                    source_workflow_id="wf-bdf26007404af6a3",
                    signal_type="trigger_structure",
                    node_or_functional_class="n8n-nodes-base.formTrigger",
                    topology_location="map_scrape_lead_intake",
                    supported_pattern_rule="capture_before_qualification",
                    confidence="explicit",
                    limitations=["HTTP enrichment is implementation variant."],
                ),
                _signal(
                    source_workflow_id="wf-bdf26007404af6a3",
                    signal_type="schema_validation",
                    node_or_functional_class="n8n-nodes-base.filter",
                    topology_location="pre_sheet_write_qualification_gate",
                    supported_pattern_rule="unqualified_leads_do_not_write",
                    confidence="probable",
                    limitations=["Filter criteria not copied from source."],
                ),
            ],
        },
        {
            "pattern_id": "draft_to_human_approval",
            "source_workflow_ids": ["wf-febea81827b8ad6b", "wf-de3f478cf93ab7e0"],
            "source_practice_ids": PATTERN_PRACTICE_IDS["draft_to_human_approval"],
            "manual_audit_id": "audit-draft_to_human_approval",
            "supporting_signals": [
                _signal(
                    source_workflow_id="wf-febea81827b8ad6b",
                    signal_type="human_decision",
                    node_or_functional_class="human_approval",
                    topology_location="content_moderator_draft_gate",
                    supported_pattern_rule="draft_review_resume",
                    confidence="probable",
                    limitations=[
                        "Same workflow supports human_approval_before_publication "
                        "via switch signal.",
                    ],
                ),
                _signal(
                    source_workflow_id="wf-febea81827b8ad6b",
                    signal_type="branch_structure",
                    node_or_functional_class="social_content",
                    topology_location="draft_state_before_external_action",
                    supported_pattern_rule="resume_only_after_authoritative_decision",
                    confidence="probable",
                    limitations=["Moderator role inferred from normalized name and categories."],
                ),
                _signal(
                    source_workflow_id="wf-de3f478cf93ab7e0",
                    signal_type="approval_gate",
                    node_or_functional_class="human_approval",
                    topology_location="legal_risk_routing_review",
                    supported_pattern_rule="draft_to_human_approval_before_action",
                    confidence="explicit",
                    limitations=["Legal domain; marketing adaptation requires owner review."],
                ),
                _signal(
                    source_workflow_id="wf-de3f478cf93ab7e0",
                    signal_type="provenance_capture",
                    node_or_functional_class="agent_orchestration",
                    topology_location="decision_lineage_after_review",
                    supported_pattern_rule="decision_lineage_preserved",
                    confidence="probable",
                    limitations=["Structured parser aids decision capture variant."],
                ),
            ],
        },
        {
            "pattern_id": "workflow_backup",
            "source_workflow_ids": ["wf-c7d30b91fd4e5694", "wf-21966e054442133e"],
            "source_practice_ids": PATTERN_PRACTICE_IDS["workflow_backup"],
            "manual_audit_id": "audit-workflow_backup",
            "supporting_signals": [
                _signal(
                    source_workflow_id="wf-c7d30b91fd4e5694",
                    signal_type="storage_action",
                    node_or_functional_class="n8n-nodes-base.gitlab",
                    topology_location="scheduled_backup_to_git",
                    supported_pattern_rule="workflow_backup_and_source_control",
                    confidence="explicit",
                    limitations=["GitLab is storage_provider variant only."],
                ),
                _signal(
                    source_workflow_id="wf-c7d30b91fd4e5694",
                    signal_type="trigger_structure",
                    node_or_functional_class="n8n-nodes-base.scheduleTrigger",
                    topology_location="backup_window_entry",
                    supported_pattern_rule="scheduled_export_not_execution",
                    confidence="explicit",
                    limitations=["n8n export node reads definitions only in abstraction."],
                ),
                _signal(
                    source_workflow_id="wf-21966e054442133e",
                    signal_type="storage_action",
                    node_or_functional_class="workflow_backup",
                    topology_location="alternate_backup_variant",
                    supported_pattern_rule="snapshot_to_storage_provider",
                    confidence="probable",
                    limitations=["Linear/cloud-cli variants are implementation-specific."],
                ),
                _signal(
                    source_workflow_id="wf-21966e054442133e",
                    signal_type="provenance_capture",
                    node_or_functional_class="n8n-nodes-base.set",
                    topology_location="backup_evidence_metadata",
                    supported_pattern_rule="backup_evidence_recorded",
                    confidence="probable",
                    limitations=["Evidence format not standardized in pilot."],
                ),
            ],
        },
        {
            "pattern_id": "error_workflow_or_recovery",
            "source_workflow_ids": ["wf-b6e1676935a48901", "wf-580f7458a07243a7"],
            "source_practice_ids": PATTERN_PRACTICE_IDS["error_workflow_or_recovery"],
            "manual_audit_id": "audit-error_workflow_or_recovery",
            "supporting_signals": [
                _signal(
                    source_workflow_id="wf-b6e1676935a48901",
                    signal_type="error_path",
                    node_or_functional_class="n8n-nodes-base.if",
                    topology_location="payment_failure_detection_branch",
                    supported_pattern_rule="explicit_error_workflow_or_recovery_path",
                    confidence="probable",
                    limitations=[
                        "Same workflow supports retry_with_idempotency via wait/retry signal.",
                    ],
                ),
                _signal(
                    source_workflow_id="wf-b6e1676935a48901",
                    signal_type="recovery_action",
                    node_or_functional_class="publication",
                    topology_location="operator_notification_on_failure",
                    supported_pattern_rule="terminal_failure_notifies_operator",
                    confidence="probable",
                    limitations=["Slack/Gmail are message_channel variants."],
                ),
                _signal(
                    source_workflow_id="wf-580f7458a07243a7",
                    signal_type="error_path",
                    node_or_functional_class="n8n-nodes-base.stopAndError",
                    topology_location="api_mock_refresh_failure_terminal",
                    supported_pattern_rule="recovery_and_terminal_failure_path",
                    confidence="explicit",
                    limitations=["SSRF finding requires elevated security review."],
                ),
                _signal(
                    source_workflow_id="wf-580f7458a07243a7",
                    signal_type="retry_structure",
                    node_or_functional_class="n8n-nodes-base.httpRequest",
                    topology_location="recoverable_http_refresh_segment",
                    supported_pattern_rule="recoverable_vs_terminal_classification",
                    confidence="probable",
                    limitations=["Dynamic URL risk documented in catalog security findings."],
                ),
            ],
        },
    ]

    return {
        "pilot_version": "0.1.0-pilot-lineage",
        "program_phase": "KB-WPL-01.3A.1",
        "multi_pattern_source_policy": (
            "A workflow may support multiple patterns when each pattern cites "
            "pattern-specific supporting_signals; no source exclusivity."
        ),
        "entries": entries,
    }


def source_support_map_semantic_hash(support_map: dict[str, Any]) -> str:
    subset = {
        "pilot_version": support_map["pilot_version"],
        "program_phase": support_map["program_phase"],
        "entries": support_map["entries"],
    }
    payload = json.dumps(subset, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
