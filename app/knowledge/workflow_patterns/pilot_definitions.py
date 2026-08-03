"""KB-WPL-01.3A pilot pattern definitions — provider-neutral abstractions."""

from __future__ import annotations

from typing import Any

from app.knowledge.workflow_patterns.practice_definitions import PATTERN_PRACTICE_IDS

ARCHIVE_ID = "arc-bots-knowledge-rar"
PROGRAM_PHASE = "KB-WPL-01.3A.1"


def _prov(source_id: str, content_hash: str | None = None) -> dict[str, str]:
    payload: dict[str, str] = {
        "source_type": "pattern_extraction_pilot",
        "archive_id": ARCHIVE_ID,
        "source_id": source_id,
        "program_phase": PROGRAM_PHASE,
    }
    if content_hash:
        payload["content_hash"] = content_hash
    return payload


def _variant(provider: str, component: str = "integration") -> dict[str, Any]:
    return {
        "provider": provider,
        "component": component,
        "documented_version": "source_catalog_0.1.0",
        "documented_at": "2026-07-23",
        "verification_status": "source_documented",
        "requires_reverification": True,
        "notes": "Observed in frozen catalog metadata only; not executed in pilot.",
        "provenance": _prov(f"variant-{provider}"),
    }


def _gates(pattern_id: str) -> list[dict[str, Any]]:
    base = _prov(f"gates-{pattern_id}")
    titles = {
        "schema_valid": "Pattern validates against workflow-pattern schema",
        "source_support_valid": "Source support gate satisfied",
        "provider_neutral": "Main flow uses functional abstractions only",
        "no_credentials": "No credential identifiers in pattern body",
        "approval_boundary_valid": "Approval boundaries match sensitivity",
        "evidence_boundary_valid": "Evidence requirements documented",
        "tenant_boundary_valid": "Tenant scope preserved",
        "idempotency_valid": "Idempotency policy matches retry behavior",
        "error_path_present": "Terminal error path documented",
        "limitations_documented": "Known limitations listed",
        "manual_review_complete": "Manual pilot audit complete",
    }
    return [
        {
            "gate_id": f"{pattern_id}-{gate_key}",
            "title": title,
            "description": title,
            "severity": "blocking",
            "verification_status": "source_documented",
            "provenance": base,
        }
        for gate_key, title in titles.items()
    ]


def _base_pattern(
    *,
    pattern_id: str,
    pattern_name: str,
    pattern_category: str,
    objective: str,
    problem_context: str,
    capability_ids: list[str],
    source_workflow_ids: list[str],
    steps: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    security_class: str,
    publication_sensitive: bool,
    billing_sensitive: bool,
    destructive: bool,
    approval_requirements: dict[str, Any],
    evidence_requirements: dict[str, Any],
    idempotency_requirements: dict[str, Any],
    retry_policy: str,
    error_paths: list[str],
    known_limitations: list[str],
    implementation_variants: list[dict[str, Any]],
    related_skill_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "pattern_id": pattern_id,
        "pattern_name": pattern_name,
        "pattern_category": pattern_category,
        "objective": objective,
        "problem_context": problem_context,
        "capability_ids": capability_ids,
        "related_skill_ids": related_skill_ids or ["ms.skill.n8n_workflow_architecture"],
        "input_contract": {
            "type": "object",
            "required": ["tenant_context", "correlation_id"],
        },
        "output_contract": {
            "type": "object",
            "required": ["status", "evidence_refs"],
        },
        "steps": steps,
        "edges": edges,
        "required_connectors": [],
        "required_tools": [],
        "approval_requirements": approval_requirements,
        "evidence_requirements": evidence_requirements,
        "idempotency_requirements": idempotency_requirements,
        "retry_policy": retry_policy,
        "timeout_policy": "pilot_default_120s",
        "rate_limit_policy": "provider_default",
        "error_paths": error_paths,
        "rollback_or_recovery": "manual_review",
        "security_class": security_class,
        "tenant_scope": "tenant_scoped",
        "personal_data_class": "unknown",
        "publication_sensitive": publication_sensitive,
        "billing_sensitive": billing_sensitive,
        "destructive": destructive,
        "implementation_variants": implementation_variants,
        "source_workflow_ids": source_workflow_ids,
        "source_practice_ids": PATTERN_PRACTICE_IDS[pattern_id],
        "known_limitations": known_limitations,
        "quality_gates": _gates(pattern_id),
        "maturity": "reviewed",
        "provenance": _prov(pattern_id),
    }


def pilot_patterns() -> list[dict[str, Any]]:
    return [
        _human_approval_before_publication(),
        _structured_llm_to_api_request(),
        _retry_with_idempotency(),
        _evidence_grounded_generation(),
        _lead_capture_to_qualification(),
        _draft_to_human_approval(),
        _workflow_backup(),
        _error_workflow_or_recovery(),
    ]


def _human_approval_before_publication() -> dict[str, Any]:
    return _base_pattern(
        pattern_id="human_approval_before_publication",
        pattern_name="Human Approval Before Publication",
        pattern_category="control_and_safety",
        objective="Block external publication until a human approves the draft.",
        problem_context="Marketing workflows that publish to external channels.",
        capability_ids=["publication", "human_approval"],
        source_workflow_ids=["wf-febea81827b8ad6b", "wf-16b82581942c24a9"],
        steps=[
            {
                "step_id": "s1",
                "step_name": "Prepare publication draft",
                "step_type": "transform",
                "security_class": "read_only",
            },
            {
                "step_id": "s2",
                "step_name": "Route to approval_interface",
                "step_type": "approval",
                "approval_gate": "before_publication",
                "security_class": "publication",
            },
            {
                "step_id": "s3",
                "step_name": "Publish to publication_target",
                "step_type": "publish",
                "security_class": "publication",
            },
            {
                "step_id": "s4",
                "step_name": "Record approval and publication evidence",
                "step_type": "evidence",
                "security_class": "write_internal",
            },
        ],
        edges=[
            {"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"},
            {"edge_id": "e2", "from_step_id": "s2", "to_step_id": "s3", "condition": "approved"},
            {
                "edge_id": "e3",
                "from_step_id": "s2",
                "to_step_id": "s1",
                "condition": "rejected",
                "on_failure": "human_review",
            },
            {"edge_id": "e4", "from_step_id": "s3", "to_step_id": "s4"},
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
        idempotency_requirements={
            "required": True,
            "policy": "dedupe_by_event_id",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        retry_policy="none",
        error_paths=["human_review", "dead_letter"],
        known_limitations=[
            "Pilot abstraction only; channel-specific payload mapping deferred to variants.",
            "Requires Connector Gateway for publication_target binding.",
        ],
        implementation_variants=[
            _variant("Telegram", "publication_target"),
            _variant("Instagram", "publication_target"),
            _variant("Gmail", "message_channel"),
        ],
    )


def _structured_llm_to_api_request() -> dict[str, Any]:
    return _base_pattern(
        pattern_id="structured_LLM_to_API_request",
        pattern_name="Structured LLM Output to API Request",
        pattern_category="ai_integration",
        objective="Generate structured output via LLM_provider and validate before transport.",
        problem_context="Lead enrichment and research agents calling external APIs.",
        capability_ids=["agent_orchestration", "lead_generation"],
        source_workflow_ids=["wf-353be45a7de607a0", "wf-b6c98c93d44e4384"],
        steps=[
            {
                "step_id": "s1",
                "step_name": "Collect input context",
                "step_type": "transform",
                "security_class": "read_only",
            },
            {
                "step_id": "s2",
                "step_name": "Invoke LLM_provider with schema contract",
                "step_type": "generate",
                "security_class": "read_only",
            },
            {
                "step_id": "s3",
                "step_name": "Validate structured payload",
                "step_type": "validate",
                "security_class": "read_only",
            },
            {
                "step_id": "s4",
                "step_name": "Send validated payload via transport",
                "step_type": "transport",
                "security_class": "write_internal",
            },
        ],
        edges=[
            {"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"},
            {"edge_id": "e2", "from_step_id": "s2", "to_step_id": "s3"},
            {
                "edge_id": "e3",
                "from_step_id": "s3",
                "to_step_id": "s4",
                "condition": "valid",
            },
            {
                "edge_id": "e4",
                "from_step_id": "s3",
                "to_step_id": "s1",
                "condition": "invalid",
                "on_failure": "human_review",
            },
        ],
        security_class="write_internal",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            "human_approval_required": False,
            "approval_gates": [],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": False,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["execution_log", "source_reference"],
        },
        idempotency_requirements={
            "required": True,
            "policy": "dedupe_by_content_hash",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        retry_policy="backoff",
        error_paths=["human_review", "dead_letter"],
        known_limitations=[
            "Schema validation rules are pilot-level; provider response shapes vary.",
            "LLM_provider hallucination risk requires human review for high-stakes writes.",
        ],
        implementation_variants=[
            _variant("OpenAI", "LLM_provider"),
            _variant("LangChain", "LLM_provider"),
        ],
    )


def _retry_with_idempotency() -> dict[str, Any]:
    return _base_pattern(
        pattern_id="retry_with_idempotency",
        pattern_name="Retry With Idempotency",
        pattern_category="reliability",
        objective="Retry transient failures without duplicate side effects.",
        problem_context="Alert and webhook workflows with external notifications.",
        capability_ids=["scheduling", "publication"],
        source_workflow_ids=["wf-b6e1676935a48901", "wf-60870942fc4ef5b9"],
        steps=[
            {
                "step_id": "s1",
                "step_name": "Assign idempotency key",
                "step_type": "transform",
                "security_class": "read_only",
            },
            {
                "step_id": "s2",
                "step_name": "Execute transport action",
                "step_type": "transport",
                "security_class": "publication",
            },
            {
                "step_id": "s3",
                "step_name": "Classify outcome",
                "step_type": "branch",
                "security_class": "read_only",
            },
            {
                "step_id": "s4",
                "step_name": "Retry with bounded backoff",
                "step_type": "retry",
                "security_class": "publication",
            },
        ],
        edges=[
            {"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"},
            {"edge_id": "e2", "from_step_id": "s2", "to_step_id": "s3"},
            {
                "edge_id": "e3",
                "from_step_id": "s3",
                "to_step_id": "s4",
                "condition": "transient_failure",
                "on_failure": "retry",
            },
            {
                "edge_id": "e4",
                "from_step_id": "s3",
                "to_step_id": "s1",
                "condition": "unknown_outcome",
                "on_failure": "human_review",
            },
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
            "evidence_classes": ["execution_log", "approval_record"],
        },
        idempotency_requirements={
            "required": True,
            "policy": "dedupe_by_event_id",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        retry_policy="bounded_backoff",
        error_paths=["human_review", "dead_letter"],
        known_limitations=[
            "Unknown transport outcomes must not auto-retry on write paths.",
            "Provider retry headers belong in implementation variants only.",
        ],
        implementation_variants=[_variant("Gmail", "message_channel")],
    )


def _evidence_grounded_generation() -> dict[str, Any]:
    return _base_pattern(
        pattern_id="evidence_grounded_generation",
        pattern_name="Evidence Grounded Generation",
        pattern_category="knowledge_and_rag",
        objective="Generate answers only from evidence_store with provenance.",
        problem_context="RAG ranking and knowledge Q&A workflows.",
        capability_ids=["rag", "agent_orchestration"],
        source_workflow_ids=["wf-b144bd6927caa092", "wf-9c87e7783b3cb118"],
        steps=[
            {
                "step_id": "s1",
                "step_name": "Retrieve evidence from evidence_store",
                "step_type": "retrieve",
                "security_class": "read_only",
            },
            {
                "step_id": "s2",
                "step_name": "Sanitize untrusted input boundary",
                "step_type": "validate",
                "security_class": "elevated_review",
            },
            {
                "step_id": "s3",
                "step_name": "Generate grounded response via LLM_provider",
                "step_type": "generate",
                "security_class": "read_only",
            },
            {
                "step_id": "s4",
                "step_name": "Attach source references or abstain",
                "step_type": "evidence",
                "security_class": "write_internal",
            },
        ],
        edges=[
            {"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"},
            {"edge_id": "e2", "from_step_id": "s2", "to_step_id": "s3", "condition": "safe_input"},
            {
                "edge_id": "e3",
                "from_step_id": "s3",
                "to_step_id": "s4",
                "condition": "grounded",
            },
            {
                "edge_id": "e4",
                "from_step_id": "s3",
                "to_step_id": "s1",
                "condition": "unsupported_claim",
                "on_failure": "human_review",
            },
        ],
        security_class="elevated_review",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            "human_approval_required": False,
            "approval_gates": [],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": False,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["source_reference", "execution_log"],
            "minimum_evidence_count": 1,
        },
        idempotency_requirements={
            "required": True,
            "policy": "dedupe_by_content_hash",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        retry_policy="none",
        error_paths=["human_review", "abstain_without_source"],
        known_limitations=[
            "No source → no grounded claim policy enforced at pattern level.",
            "Prompt-injection boundary requires elevated review before LLM_provider call.",
            "Vector store specifics deferred to implementation variants.",
        ],
        implementation_variants=[
            _variant("OpenAI", "LLM_provider"),
            _variant("LangChain", "LLM_provider"),
        ],
    )


def _lead_capture_to_qualification() -> dict[str, Any]:
    return _base_pattern(
        pattern_id="lead_capture_to_qualification",
        pattern_name="Lead Capture to Qualification",
        pattern_category="lead_generation",
        objective="Capture inbound lead signals and qualify before CRM_provider write.",
        problem_context="Lead list enrichment and map-based prospecting flows.",
        capability_ids=["lead_generation"],
        source_workflow_ids=["wf-353be45a7de607a0", "wf-bdf26007404af6a3"],
        steps=[
            {
                "step_id": "s1",
                "step_name": "Capture lead signal",
                "step_type": "trigger",
                "security_class": "read_only",
            },
            {
                "step_id": "s2",
                "step_name": "Normalize lead profile",
                "step_type": "transform",
                "security_class": "read_only",
            },
            {
                "step_id": "s3",
                "step_name": "Qualify via LLM_provider rules",
                "step_type": "validate",
                "security_class": "elevated_review",
            },
            {
                "step_id": "s4",
                "step_name": "Write qualified lead to CRM_provider",
                "step_type": "write",
                "security_class": "write_internal",
            },
        ],
        edges=[
            {"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"},
            {"edge_id": "e2", "from_step_id": "s2", "to_step_id": "s3"},
            {"edge_id": "e3", "from_step_id": "s3", "to_step_id": "s4", "condition": "qualified"},
            {
                "edge_id": "e4",
                "from_step_id": "s3",
                "to_step_id": "s2",
                "condition": "unqualified",
                "on_failure": "stop",
            },
        ],
        security_class="write_internal",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            "human_approval_required": False,
            "approval_gates": ["before_write"],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": False,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["source_reference", "execution_log"],
        },
        idempotency_requirements={
            "required": True,
            "policy": "dedupe_by_event_id",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        retry_policy="none",
        error_paths=["human_review", "dead_letter"],
        known_limitations=[
            "Personal-data handling requires tenant policy review before production.",
            "CRM_provider field mapping not included in pilot abstraction.",
        ],
        implementation_variants=[
            _variant("OpenAI", "LLM_provider"),
            _variant("Google Sheets", "storage_provider"),
        ],
    )


def _draft_to_human_approval() -> dict[str, Any]:
    return _base_pattern(
        pattern_id="draft_to_human_approval",
        pattern_name="Draft to Human Approval",
        pattern_category="control_and_safety",
        objective="Hold content in draft state until human approve/reject decision.",
        problem_context="Moderation and legal review workflows before any external action.",
        capability_ids=["human_approval", "publication"],
        source_workflow_ids=["wf-febea81827b8ad6b", "wf-de3f478cf93ab7e0"],
        steps=[
            {
                "step_id": "s1",
                "step_name": "Create draft artifact",
                "step_type": "transform",
                "security_class": "read_only",
            },
            {
                "step_id": "s2",
                "step_name": "Present draft on approval_interface",
                "step_type": "approval",
                "approval_gate": "before_external_action",
                "security_class": "elevated_review",
            },
            {
                "step_id": "s3",
                "step_name": "Resume only after authoritative decision",
                "step_type": "branch",
                "security_class": "read_only",
            },
            {
                "step_id": "s4",
                "step_name": "Persist decision lineage",
                "step_type": "evidence",
                "security_class": "write_internal",
            },
        ],
        edges=[
            {"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"},
            {"edge_id": "e2", "from_step_id": "s2", "to_step_id": "s3"},
            {
                "edge_id": "e3",
                "from_step_id": "s3",
                "to_step_id": "s4",
                "condition": "decision_recorded",
            },
            {
                "edge_id": "e4",
                "from_step_id": "s3",
                "to_step_id": "s1",
                "condition": "rejected",
                "on_failure": "human_review",
            },
        ],
        security_class="elevated_review",
        publication_sensitive=True,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            "human_approval_required": True,
            "approval_gates": ["before_publication", "before_external_action"],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": True,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["approval_record", "execution_log"],
            "minimum_evidence_count": 2,
        },
        idempotency_requirements={
            "required": True,
            "policy": "dedupe_by_event_id",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        retry_policy="none",
        error_paths=["human_review"],
        known_limitations=[
            "Decision lineage format not standardized across approval_interface variants.",
            "Pilot does not include auto-resume after timeout.",
        ],
        implementation_variants=[_variant("Slack", "approval_interface")],
    )


def _workflow_backup() -> dict[str, Any]:
    return _base_pattern(
        pattern_id="workflow_backup",
        pattern_name="Workflow Backup to Storage",
        pattern_category="operations",
        objective="Export workflow definitions to storage_provider on schedule.",
        problem_context="Operational backup flows observed in catalog metadata.",
        capability_ids=["workflow_backup", "scheduling"],
        source_workflow_ids=["wf-c7d30b91fd4e5694", "wf-21966e054442133e"],
        steps=[
            {
                "step_id": "s1",
                "step_name": "Trigger backup window",
                "step_type": "trigger",
                "security_class": "read_only",
            },
            {
                "step_id": "s2",
                "step_name": "List or export workflow definitions",
                "step_type": "read",
                "security_class": "read_only",
            },
            {
                "step_id": "s3",
                "step_name": "Write snapshot to storage_provider",
                "step_type": "write",
                "security_class": "write_internal",
            },
            {
                "step_id": "s4",
                "step_name": "Record backup evidence",
                "step_type": "evidence",
                "security_class": "write_internal",
            },
        ],
        edges=[
            {"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"},
            {"edge_id": "e2", "from_step_id": "s2", "to_step_id": "s3"},
            {"edge_id": "e3", "from_step_id": "s3", "to_step_id": "s4"},
        ],
        security_class="write_internal",
        publication_sensitive=False,
        billing_sensitive=False,
        destructive=False,
        approval_requirements={
            "human_approval_required": False,
            "approval_gates": ["before_write"],
            "auto_approval_allowed": False,
            "spend_approval_required": False,
            "publication_approval_required": False,
        },
        evidence_requirements={
            "required": True,
            "evidence_classes": ["execution_log", "audit_finding"],
        },
        idempotency_requirements={
            "required": True,
            "policy": "dedupe_by_content_hash",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        retry_policy="backoff",
        error_paths=["human_review", "dead_letter"],
        known_limitations=[
            "Backup scope limited to metadata-evidenced export patterns.",
            "Restore operations out of pilot scope.",
        ],
        implementation_variants=[
            _variant("GitLab", "storage_provider"),
            _variant("Google Drive", "storage_provider"),
            _variant("n8n", "workflow_platform"),
        ],
    )


def _error_workflow_or_recovery() -> dict[str, Any]:
    return _base_pattern(
        pattern_id="error_workflow_or_recovery",
        pattern_name="Error Workflow or Recovery Path",
        pattern_category="reliability",
        objective="Route failures to recovery or operator review without silent loss.",
        problem_context="Alerting and API refresh workflows with failure branches.",
        capability_ids=["publication", "scheduling"],
        source_workflow_ids=["wf-b6e1676935a48901", "wf-580f7458a07243a7"],
        steps=[
            {
                "step_id": "s1",
                "step_name": "Execute primary action",
                "step_type": "transport",
                "security_class": "publication",
            },
            {
                "step_id": "s2",
                "step_name": "Detect failure class",
                "step_type": "branch",
                "security_class": "read_only",
            },
            {
                "step_id": "s3",
                "step_name": "Invoke recovery or error_workflow",
                "step_type": "recover",
                "security_class": "write_internal",
            },
            {
                "step_id": "s4",
                "step_name": "Notify operator via message_channel",
                "step_type": "notify",
                "security_class": "publication",
            },
        ],
        edges=[
            {"edge_id": "e1", "from_step_id": "s1", "to_step_id": "s2"},
            {
                "edge_id": "e2",
                "from_step_id": "s2",
                "to_step_id": "s3",
                "condition": "recoverable",
                "on_failure": "fallback",
            },
            {
                "edge_id": "e3",
                "from_step_id": "s2",
                "to_step_id": "s4",
                "condition": "terminal_failure",
                "on_failure": "human_review",
            },
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
            "evidence_classes": ["execution_log", "approval_record"],
        },
        idempotency_requirements={
            "required": True,
            "policy": "dedupe_by_event_id",
            "unknown_outcome_auto_retry": False,
            "duplicate_event_prevention": True,
        },
        retry_policy="bounded_backoff",
        error_paths=["human_review", "dead_letter", "fallback"],
        known_limitations=[
            "Recovery semantics vary by transport provider.",
            "Error workflow linkage not executed or validated in pilot.",
        ],
        implementation_variants=[_variant("Gmail", "message_channel")],
    )
