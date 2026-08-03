# Practice Verification Matrix — KB-WPL-01.3C

## Verification status discipline

| Status | Meaning | Allowed when |
|--------|---------|--------------|
| source_documented | Archive/source wording preserved | Default for core practices |
| regression_tested | Deterministic test reference exists | Pilot practices with test refs |
| reproduced | Actual reproduction evidence | **Forbidden** without evidence |

Green schema validation alone is **insufficient** for `regression_tested` or `reproduced`.

## Pilot practices (11)

| practice_id | verification_status | test reference |
|-------------|---------------------|----------------|
| idempotency_before_retry | regression_tested | test_23_retry_requires_idempotency |
| human_approval_before_write_or_publication | source_documented | — |
| evidence_grounded_generation | source_documented | — |
| explicit_error_workflow | source_documented | — |
| draft_review_resume | source_documented | — |
| lead_qualification_boundary | source_documented | — |
| prompt_injection_boundary | source_documented | — |
| structured_output_validation | source_documented | — |
| workflow_backup_before_change | source_documented | — |
| rag_source_reference | source_documented | — |
| publication_evidence_capture | source_documented | — |

## Core practices (13)

All core practices: `verification_status=source_documented`.

| practice_id | related pattern |
|-------------|-----------------|
| pagination_until_exhausted | pagination_and_batching |
| bounded_batch_processing | pagination_and_batching |
| checkpoint_before_expensive_step | checkpoint_and_resume |
| terminal_dead_letter_handling | dead_letter_queue |
| rate_limit_backoff | provider_rate_limit_handling |
| quality_gate_before_handoff | quality_gate_after_generation |
| specialist_scope_isolation | specialist_subworkflow |
| supervisor_does_not_execute_tools | supervisor_pattern |
| tool_workflow_permission_boundary | tool_workflow_separation |
| manual_edit_resume | human_edit_then_resume |
| post_publish_evidence_capture | publication_confirmation |
| source_lineage_preservation | source_lineage_preservation |
| feedback_to_knowledge_candidate | customer_feedback_to_learning_candidate |

## Provider/version claims

All provider-specific claims include `documented_version`, `documented_at`,
`requires_reverification=true`. No timeless guarantees.
