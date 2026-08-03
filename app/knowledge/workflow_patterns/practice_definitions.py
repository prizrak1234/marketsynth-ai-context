"""KB-WPL-01.3A.1 pilot PracticeRecord definitions — archive-backed lineage."""

from __future__ import annotations

from typing import Any

PROGRAM_PHASE = "KB-WPL-01.3A.1"
ARCHIVE_SKILLS = "arc-skills-dlya-peredachi"
ARCHIVE_SKILLS_HASH = "362eb1101baf6c9270990ac274925d2b5d896fbf9122ab0671323a02ba32c7f9"
ARCHIVE_BOTS = "arc-bots-knowledge-rar"
ARCHIVE_BOTS_HASH = "59d69ddbd9c6783af2526276bfce4025dde374dc4d8d228927303820d5f03e2b"
INTERNAL_DOCS = "marketsynth-accepted-internal"

METHODOLOGY_REL = "n8n-knowledge-base/references/methodology.md"
METHODOLOGY_HASH = "727666fe4bb10519fe05561f2a938336b11df28718e472bc39c4e7fc52acd8e3"
AI_AGENTS_REL = "n8n-knowledge-base/references/ai-agents.md"
AI_AGENTS_HASH = "453a415870a0c9cbef2accddecd5e19fd833b05c741099fd82df421e5e5a3620"
QUALITY_GATE_REL = "Стандарт/Скиллы/06_QUALITY_GATE.md"
QUALITY_GATE_HASH = "e83c24077af14b963ee9ac6a2ac8a5032b26b15d46c7af191b0484148138af21"
METHODOLOGY_DOC_REL = "docs/architecture/WORKFLOW-PATTERN-EXTRACTION-METHODOLOGY.md"


def _prov(source_id: str, archive_id: str = ARCHIVE_SKILLS) -> dict[str, str]:
    return {
        "source_type": "practice_lineage_pilot",
        "archive_id": archive_id,
        "source_id": source_id,
        "program_phase": PROGRAM_PHASE,
    }


def _archive_ref(
    *,
    archive_id: str,
    archive_hash: str,
    relative_path: str,
    content_hash: str,
    source_id: str,
    category: str = "engineering_methodology",
) -> dict[str, Any]:
    return {
        "archive_id": archive_id,
        "archive_hash": archive_hash,
        "relative_path": relative_path,
        "content_hash": content_hash,
        "source_category": category,
        "provenance": _prov(source_id, archive_id),
    }


def _internal_ref(relative_path: str, content_hash: str, source_id: str) -> dict[str, Any]:
    return {
        "archive_id": INTERNAL_DOCS,
        "relative_path": relative_path,
        "content_hash": content_hash,
        "source_category": "accepted_internal_documentation",
        "provenance": _prov(source_id, INTERNAL_DOCS),
    }


def _provider_scope(
    provider: str = "n8n",
    component: str = "workflow_platform",
    version: str = "source_archive_methodology",
    status: str = "source_documented",
) -> dict[str, Any]:
    return {
        "provider": provider,
        "component": component,
        "documented_version": version,
        "documented_at": "2026-07-23",
        "verification_status": status,
        "requires_reverification": True,
        "notes": "Archive methodology; not re-executed in pilot hardening.",
        "provenance": _prov(f"scope-{provider}"),
    }


def _practice(
    *,
    practice_id: str,
    title: str,
    domain: str,
    context: str,
    problem: str,
    recommended_practice: str,
    rationale: str,
    implementation_pattern: str,
    related_pattern_ids: list[str],
    source_references: list[dict[str, Any]],
    verification_status: str = "source_documented",
    tested_environment: str = "archive_metadata_only",
    prerequisites: list[str] | None = None,
    failure_modes: list[str] | None = None,
    security_notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "practice_id": practice_id,
        "title": title,
        "domain": domain,
        "context": context,
        "problem": problem,
        "recommended_practice": recommended_practice,
        "rationale": rationale,
        "prerequisites": prerequisites or [],
        "implementation_pattern": implementation_pattern,
        "failure_modes": failure_modes or [],
        "security_notes": security_notes or [],
        "provider_version_scope": [_provider_scope()],
        "tested_environment": tested_environment,
        "verification_status": verification_status,
        "source_references": source_references,
        "related_pattern_ids": related_pattern_ids,
        "tenant_scope": "tenant_scoped",
        "provenance": _prov(practice_id),
    }


def pilot_practices() -> list[dict[str, Any]]:
    archive_methodology = _archive_ref(
        archive_id=ARCHIVE_SKILLS,
        archive_hash=ARCHIVE_SKILLS_HASH,
        relative_path=METHODOLOGY_REL,
        content_hash=METHODOLOGY_HASH,
        source_id="ref-methodology",
    )
    archive_ai = _archive_ref(
        archive_id=ARCHIVE_SKILLS,
        archive_hash=ARCHIVE_SKILLS_HASH,
        relative_path=AI_AGENTS_REL,
        content_hash=AI_AGENTS_HASH,
        source_id="ref-ai-agents",
    )
    archive_quality = _archive_ref(
        archive_id=ARCHIVE_BOTS,
        archive_hash=ARCHIVE_BOTS_HASH,
        relative_path=QUALITY_GATE_REL,
        content_hash=QUALITY_GATE_HASH,
        source_id="ref-quality-gate",
        category="skill_quality",
    )

    return [
        _practice(
            practice_id="human_approval_before_write_or_publication",
            title="Human approval before write or publication",
            domain="control_and_safety",
            context="External publication and sensitive write paths in marketing workflows.",
            problem=(
                "Auto-publishing or writing without human gate causes brand and compliance risk."
            ),
            recommended_practice=(
                "Route drafts through approval_interface before publication_target or "
                "CRM_provider write; block resume until authoritative human decision."
            ),
            rationale=(
                "Archive methodology §5 requires explicit validation and error paths; "
                "quality gate docs reinforce human review before external action."
            ),
            implementation_pattern=(
                "draft → approval_interface → branch(approved|rejected) → publish|revise"
            ),
            related_pattern_ids=[
                "human_approval_before_publication",
                "draft_to_human_approval",
            ],
            source_references=[archive_methodology, archive_quality],
            security_notes=[
                "Publication without approval is a blocking defect for pilot patterns.",
            ],
        ),
        _practice(
            practice_id="structured_output_before_API_call",
            title="Structured output before API call",
            domain="ai_integration",
            context="LLM-assisted enrichment and research agents calling downstream APIs.",
            problem="Unvalidated LLM JSON causes silent downstream API failures.",
            recommended_practice=(
                "Require schema validation step after LLM_provider and before transport; "
                "invalid payloads route to human_review, never auto-send."
            ),
            rationale=(
                "Archive ai-agents.md AI-Р3 documents structured JSON handling for OpenAI nodes; "
                "catalog sources show outputParserStructured and OpenAI nodes."
            ),
            implementation_pattern="LLM_provider → validate(schema) → transport | human_review",
            related_pattern_ids=["structured_LLM_to_API_request"],
            source_references=[archive_ai, archive_methodology],
            failure_modes=[
                "Empty parsed fields when text is dict not string",
                "Schema drift across providers",
            ],
        ),
        _practice(
            practice_id="idempotency_before_retry",
            title="Idempotency before retry",
            domain="reliability",
            context="Alert and notification workflows with Retry On Fail on HTTP or messaging.",
            problem="Retries on non-idempotent writes duplicate side effects.",
            recommended_practice=(
                "Assign deduplication key before transport; classify read-only vs idempotent write "
                "before enabling retry; cap attempts with terminal failure path."
            ),
            rationale=(
                "Archive methodology §5 recommends Retry On Fail on HTTP with bounded attempts."
            ),
            implementation_pattern="assign_key → transport → classify → retry(transient)|terminal",
            related_pattern_ids=["retry_with_idempotency"],
            source_references=[archive_methodology],
            verification_status="regression_tested",
            tested_environment="tests/test_kb_wpl_01_3a_pattern_extraction_pilot.py::test_23_retry_requires_idempotency",
        ),
        _practice(
            practice_id="unknown_outcome_write_no_auto_retry",
            title="Unknown outcome write must not auto-retry",
            domain="reliability",
            context="Transport layers where success/failure is ambiguous after timeout.",
            problem="Auto-retry on unknown write outcome may duplicate charges or messages.",
            recommended_practice=(
                "When outcome is unknown on a write path, route to human_review or reconciliation; "
                "never auto-retry without idempotency proof."
            ),
            rationale=(
                "Pilot pattern invariant enforced by semantic tests; "
                "aligns with methodology error paths."
            ),
            implementation_pattern=(
                "classify_outcome → unknown → human_review (no auto-retry on write)"
            ),
            related_pattern_ids=["retry_with_idempotency"],
            source_references=[archive_methodology],
            verification_status="regression_tested",
            tested_environment=(
                "tests/test_kb_wpl_01_3a_pattern_extraction_pilot.py::test_24_unknown_outcome_no_auto_retry"
            ),
        ),
        _practice(
            practice_id="evidence_grounded_generation",
            title="Evidence grounded generation",
            domain="knowledge_and_rag",
            context="RAG ranking, vector Q&A, and agent tool retrieval workflows.",
            problem=(
                "LLM answers without retrieval provenance produce unsupported marketing claims."
            ),
            recommended_practice=(
                "Retrieve from evidence_store; attach source references; "
                "abstain when retrieval empty; no source → no grounded claim."
            ),
            rationale=(
                "Archive ai-agents.md AI-Р4 requires tool output as sole factual basis; "
                "catalog RAG workflows show vector store and agent tool chains."
            ),
            implementation_pattern="retrieve → sanitize → generate → attach_refs | abstain",
            related_pattern_ids=["evidence_grounded_generation"],
            source_references=[archive_ai, archive_methodology],
            verification_status="regression_tested",
            tested_environment=(
                "tests/test_kb_wpl_01_3a_pattern_extraction_pilot.py::test_26_rag_preserves_source_references"
            ),
        ),
        _practice(
            practice_id="prompt_injection_boundary",
            title="Prompt injection boundary for RAG inputs",
            domain="knowledge_and_rag",
            context="Untrusted user or web content fed into LLM_provider via agent tools.",
            problem="Malicious retrieved content can override system instructions.",
            recommended_practice=(
                "Sanitize untrusted input before LLM_provider; treat retrieval as untrusted; "
                "elevated_review when injection markers detected in catalog metadata."
            ),
            rationale=(
                "Catalog flags untrusted_content_to_llm on RAG sources; "
                "methodology §10 treats sensitive data and external input cautiously."
            ),
            implementation_pattern="retrieve → injection_boundary_check → generate | human_review",
            related_pattern_ids=["evidence_grounded_generation"],
            source_references=[archive_ai, archive_methodology],
            verification_status="regression_tested",
            tested_environment=(
                "tests/test_kb_wpl_01_3a_pattern_extraction_pilot.py::test_27_rag_injection_boundary"
            ),
            security_notes=[
                "Catalog security finding untrusted_content_to_llm is a review trigger.",
            ],
        ),
        _practice(
            practice_id="lead_qualification_boundary",
            title="Lead qualification boundary before CRM write",
            domain="lead_generation",
            context="Inbound lead capture from forms, maps, and batch enrichment.",
            problem="Unqualified leads pollute CRM_provider and waste outreach budget.",
            recommended_practice=(
                "Normalize lead profile → qualify via rules or LLM_provider → "
                "write only when qualified; unqualified path stops without CRM write."
            ),
            rationale=(
                "Catalog lead workflows combine capture triggers, IF branches, "
                "and batch processing before sheet or API writes."
            ),
            implementation_pattern="capture → normalize → qualify → CRM_write | stop",
            related_pattern_ids=["lead_capture_to_qualification"],
            source_references=[archive_methodology],
        ),
        _practice(
            practice_id="draft_review_resume",
            title="Draft review and resume after human decision",
            domain="control_and_safety",
            context="Moderation and legal review before any external action resumes.",
            problem="Auto-resume after draft submission bypasses human edit/reject authority.",
            recommended_practice=(
                "Hold draft state; present on approval_interface; resume only after "
                "approve/reject decision; persist decision lineage."
            ),
            rationale=(
                "Methodology §8 requires explicit customer agreement before assembly; "
                "maps to draft→approval→resume in moderation workflows."
            ),
            implementation_pattern=(
                "draft → approval_interface → decision → resume|revise → evidence"
            ),
            related_pattern_ids=["draft_to_human_approval"],
            source_references=[archive_methodology, archive_quality],
        ),
        _practice(
            practice_id="workflow_backup_and_source_control",
            title="Workflow backup and source control",
            domain="operations",
            context="Scheduled export of workflow definitions to storage_provider.",
            problem="Live workflow drift without versioned backup complicates recovery.",
            recommended_practice=(
                "Schedule trigger → list/export definitions → write snapshot to storage_provider → "
                "record backup evidence; never treat backup as executable activation."
            ),
            rationale=(
                "Methodology §9 requires re-export snapshots after confirmed working state; "
                "catalog backup workflows use n8n/GitLab schedule patterns."
            ),
            implementation_pattern="schedule → export → storage_write → evidence",
            related_pattern_ids=["workflow_backup"],
            source_references=[archive_methodology],
        ),
        _practice(
            practice_id="explicit_error_workflow",
            title="Explicit error workflow assignment",
            domain="reliability",
            context="Production workflows with external side effects.",
            problem="Silent failures lose operator visibility and audit trail.",
            recommended_practice=(
                "Assign dedicated error_workflow: Error Trigger → format context → notify via "
                "message_channel with workflow name, node, error, timestamp."
            ),
            rationale="Archive methodology §5: Error Workflow mandatory for production workflows.",
            implementation_pattern="primary_flow || error_trigger → format → notify",
            related_pattern_ids=["error_workflow_or_recovery"],
            source_references=[archive_methodology],
        ),
        _practice(
            practice_id="recovery_and_terminal_failure_path",
            title="Recovery and terminal failure path",
            domain="reliability",
            context="API refresh and alert workflows with recoverable vs terminal failures.",
            problem="Infinite retry loops or silent stop without operator escalation.",
            recommended_practice=(
                "Classify failure: recoverable → bounded retry/recovery_action; "
                "terminal → notify operator and dead_letter; never silent loss."
            ),
            rationale=(
                "Methodology pairs retry with error workflow; catalog alert flows use IF branches "
                "and stopAndError nodes."
            ),
            implementation_pattern="execute → classify → recover|notify_terminal",
            related_pattern_ids=["error_workflow_or_recovery", "retry_with_idempotency"],
            source_references=[archive_methodology],
            verification_status="regression_tested",
            tested_environment=(
                "tests/test_kb_wpl_01_3a_pattern_extraction_pilot.py::test_29_error_recovery_path_present"
            ),
        ),
    ]


PATTERN_PRACTICE_IDS: dict[str, list[str]] = {
    "human_approval_before_publication": ["human_approval_before_write_or_publication"],
    "structured_LLM_to_API_request": ["structured_output_before_API_call"],
    "retry_with_idempotency": [
        "idempotency_before_retry",
        "unknown_outcome_write_no_auto_retry",
    ],
    "evidence_grounded_generation": [
        "evidence_grounded_generation",
        "prompt_injection_boundary",
    ],
    "lead_capture_to_qualification": ["lead_qualification_boundary"],
    "draft_to_human_approval": [
        "draft_review_resume",
        "human_approval_before_write_or_publication",
    ],
    "workflow_backup": ["workflow_backup_and_source_control"],
    "error_workflow_or_recovery": [
        "explicit_error_workflow",
        "recovery_and_terminal_failure_path",
    ],
}
