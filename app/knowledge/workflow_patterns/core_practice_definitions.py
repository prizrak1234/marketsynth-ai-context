"""KB-WPL-01.3B core PracticeRecord definitions."""

from __future__ import annotations

from typing import Any

from app.knowledge.workflow_patterns.practice_definitions import (
    AI_AGENTS_HASH,
    AI_AGENTS_REL,
    ARCHIVE_SKILLS,
    ARCHIVE_SKILLS_HASH,
    METHODOLOGY_HASH,
    METHODOLOGY_REL,
    _archive_ref,
    _practice,
    _prov,
)

PROGRAM_PHASE = "KB-WPL-01.3B"


def _core_practice(**kwargs: Any) -> dict[str, Any]:
    record = _practice(**kwargs)
    record["provenance"] = _prov(kwargs["practice_id"], ARCHIVE_SKILLS)
    record["provenance"]["program_phase"] = PROGRAM_PHASE
    return record


def core_practices() -> list[dict[str, Any]]:
    methodology = _archive_ref(
        archive_id=ARCHIVE_SKILLS,
        archive_hash=ARCHIVE_SKILLS_HASH,
        relative_path=METHODOLOGY_REL,
        content_hash=METHODOLOGY_HASH,
        source_id="ref-methodology-core",
    )
    ai_agents = _archive_ref(
        archive_id=ARCHIVE_SKILLS,
        archive_hash=ARCHIVE_SKILLS_HASH,
        relative_path=AI_AGENTS_REL,
        content_hash=AI_AGENTS_HASH,
        source_id="ref-ai-agents-core",
    )

    return [
        _core_practice(
            practice_id="pagination_until_exhausted",
            title="Pagination until exhausted",
            domain="data_flow",
            context="API and sheet reads that must traverse all pages safely.",
            problem="Single-page reads silently drop records at scale.",
            recommended_practice=(
                "Loop with explicit termination: empty page, max pages, or cursor end; "
                "never infinite pagination without cap."
            ),
            rationale=(
                "Methodology recommends Split In Batches and bounded loops for large datasets."
            ),
            implementation_pattern="fetch_page → process → has_more? → fetch_next | complete",
            related_pattern_ids=["pagination_and_batching"],
            source_references=[methodology],
        ),
        _core_practice(
            practice_id="bounded_batch_processing",
            title="Bounded batch processing",
            domain="data_flow",
            context="High-volume enrichment and notification workflows.",
            problem="Unbounded batch size causes rate limits and memory pressure.",
            recommended_practice=(
                "splitInBatches equivalent with configured max_batch_size; "
                "pause between batches when provider limits apply."
            ),
            rationale="Catalog batch workflows combine splitInBatches with schedule triggers.",
            implementation_pattern="split_batch(max=N) → process → wait_if_needed → next_batch",
            related_pattern_ids=["pagination_and_batching"],
            source_references=[methodology],
        ),
        _core_practice(
            practice_id="checkpoint_before_expensive_step",
            title="Checkpoint before expensive step",
            domain="reliability",
            context="Long-running generation or media conversion pipelines.",
            problem="Failure after expensive step loses progress and repeats cost.",
            recommended_practice=(
                "Persist checkpoint state before LLM_provider or media step; "
                "resume from checkpoint_id on retry."
            ),
            rationale="Methodology §9 snapshot discipline maps to checkpoint/resume semantics.",
            implementation_pattern="checkpoint_write → expensive_step → mark_complete",
            related_pattern_ids=["checkpoint_and_resume"],
            source_references=[methodology],
        ),
        _core_practice(
            practice_id="terminal_dead_letter_handling",
            title="Terminal dead-letter handling",
            domain="reliability",
            context="Failed items after retry exhaustion.",
            problem="Silent drop of failed records loses audit trail.",
            recommended_practice=(
                "Route terminal failures to dead_letter_queue with correlation_id, "
                "error class, and operator notification."
            ),
            rationale=(
                "Pairs with error workflow methodology; catalog alert flows use terminal branches."
            ),
            implementation_pattern="retry_exhausted → dead_letter → notify_operator",
            related_pattern_ids=["dead_letter_queue"],
            source_references=[methodology],
        ),
        _core_practice(
            practice_id="rate_limit_backoff",
            title="Rate limit backoff",
            domain="reliability",
            context="HTTP and LLM_provider calls with provider throttling.",
            problem="Immediate retry on 429 amplifies ban risk.",
            recommended_practice=(
                "Detect rate_limit response; apply exponential backoff with jitter; "
                "respect Retry-After when present in implementation variant only."
            ),
            rationale="Methodology §5 Retry On Fail with bounded attempts.",
            implementation_pattern="call → rate_limited → backoff → retry|circuit_break",
            related_pattern_ids=["provider_rate_limit_handling"],
            source_references=[methodology],
        ),
        _core_practice(
            practice_id="quality_gate_before_handoff",
            title="Quality gate before handoff",
            domain="ai_integration",
            context="LLM-generated content before publication or CRM write.",
            problem="Invalid generated output propagates to external systems.",
            recommended_practice=(
                "Validate structured output against schema; block handoff on failure; "
                "route to human_review or revision loop."
            ),
            rationale=(
                "Archive ai-agents structured output handling; "
                "catalog outputParserStructured usage."
            ),
            implementation_pattern="generate → validate → pass|block|revise",
            related_pattern_ids=["quality_gate_after_generation"],
            source_references=[ai_agents, methodology],
        ),
        _core_practice(
            practice_id="supervisor_does_not_execute_tools",
            title="Supervisor does not execute tools directly",
            domain="ai_integration",
            context="Multi-agent governance and orchestration workflows.",
            problem="Supervisor with direct tool access bypasses permission boundaries.",
            recommended_practice=(
                "Supervisor delegates to specialist_subworkflow; "
                "supervisor step_type=orchestrate only, no undeclared tool execution."
            ),
            rationale="Archive ai-agents agent+agentTool topology in catalog governance workflows.",
            implementation_pattern="supervisor → delegate → specialist → aggregate",
            related_pattern_ids=["supervisor_pattern"],
            source_references=[ai_agents],
        ),
        _core_practice(
            practice_id="specialist_scope_isolation",
            title="Specialist scope isolation",
            domain="ai_integration",
            context="Sub-workflows invoked as agent tools.",
            problem="Specialist exceeding declared scope creates unreviewed side effects.",
            recommended_practice=(
                "Declare specialist scope in input_contract; reject undeclared writes; "
                "tool_workflow boundary enforced."
            ),
            rationale="Methodology modular sub-workflow pattern; catalog agentTool chains.",
            implementation_pattern="scope_check → execute_in_boundary → return_result",
            related_pattern_ids=["specialist_subworkflow", "tool_workflow_separation"],
            source_references=[methodology, ai_agents],
        ),
        _core_practice(
            practice_id="tool_workflow_permission_boundary",
            title="Tool workflow permission boundary",
            domain="ai_integration",
            context="Agent tools implemented as separate workflows.",
            problem="Tool workflow inherits full agent permissions.",
            recommended_practice=(
                "Tool workflow accepts only allowlisted operations; "
                "no credential escalation across tool boundary."
            ),
            rationale="Catalog toolWorkflow nodes with isolated triggers.",
            implementation_pattern="tool_trigger → allowlist_check → minimal_action",
            related_pattern_ids=["tool_workflow_separation"],
            source_references=[ai_agents],
        ),
        _core_practice(
            practice_id="manual_edit_resume",
            title="Manual edit then resume",
            domain="control_and_safety",
            context="Human correction of AI drafts before continuation.",
            problem="Auto-continuing after generation skips human edits.",
            recommended_practice=(
                "Pause after draft; human_edit on approval_interface; "
                "resume only with authoritative edited artifact reference."
            ),
            rationale="Extends draft_review_resume for explicit edit step.",
            implementation_pattern="draft → human_edit → resume_with_lineage",
            related_pattern_ids=["human_edit_then_resume"],
            source_references=[methodology],
        ),
        _core_practice(
            practice_id="post_publish_evidence_capture",
            title="Post-publish evidence capture",
            domain="control_and_safety",
            context="External publication confirmation workflows.",
            problem="Publication without confirmation evidence breaks audit trail.",
            recommended_practice=(
                "After publication_target action, capture confirmation evidence "
                "(message_id, timestamp, channel_ref); require human approval before send."
            ),
            rationale="Publication-sensitive catalog workflows with Gmail/social side effects.",
            implementation_pattern="approve → publish → capture_confirmation_evidence",
            related_pattern_ids=["publication_confirmation"],
            source_references=[methodology],
        ),
        _core_practice(
            practice_id="source_lineage_preservation",
            title="Source lineage preservation",
            domain="data_flow",
            context="Research, SEO, and content pipelines producing derived artifacts.",
            problem="Derived content loses traceability to source records.",
            recommended_practice=(
                "Carry source_reference through every transform; "
                "output must include lineage chain and content_hash."
            ),
            rationale="Methodology documentation and index discipline; aggregate nodes in catalog.",
            implementation_pattern="ingest → transform* → output+lineage_refs",
            related_pattern_ids=["source_lineage_preservation"],
            source_references=[methodology],
        ),
        _core_practice(
            practice_id="feedback_to_knowledge_candidate",
            title="Feedback to knowledge candidate",
            domain="marketing_learning",
            context="Customer feedback and support interactions.",
            problem="Feedback lost instead of becoming governed knowledge candidate.",
            recommended_practice=(
                "Emit knowledge_candidate draft with source evidence, confidence, "
                "contradictions, tenant_scope; owner_review_required=true; "
                "never auto-promote to canonical Knowledge Core."
            ),
            rationale="Learning boundary: candidate only, no CIM/canonical mutation.",
            implementation_pattern=(
                "feedback → normalize → knowledge_candidate_draft → review_queue"
            ),
            related_pattern_ids=["customer_feedback_to_learning_candidate"],
            source_references=[methodology],
            security_notes=[
                "Must not modify canonical Knowledge Core or cross tenants.",
            ],
        ),
    ]


CORE_PATTERN_PRACTICE_IDS: dict[str, list[str]] = {
    "pagination_and_batching": ["pagination_until_exhausted", "bounded_batch_processing"],
    "checkpoint_and_resume": ["checkpoint_before_expensive_step"],
    "dead_letter_queue": ["terminal_dead_letter_handling"],
    "provider_rate_limit_handling": ["rate_limit_backoff"],
    "quality_gate_after_generation": ["quality_gate_before_handoff"],
    "specialist_subworkflow": ["specialist_scope_isolation"],
    "supervisor_pattern": ["supervisor_does_not_execute_tools"],
    "tool_workflow_separation": [
        "tool_workflow_permission_boundary",
        "specialist_scope_isolation",
    ],
    "human_edit_then_resume": ["manual_edit_resume"],
    "publication_confirmation": ["post_publish_evidence_capture"],
    "source_lineage_preservation": ["source_lineage_preservation"],
    "customer_feedback_to_learning_candidate": ["feedback_to_knowledge_candidate"],
}
