# Practice Lineage — KB-WPL-01.3B

13 new PracticeRecords in `practices/core/`. Pilot practices in `practices/pilot/` unchanged.

## Core PracticeRecords

| practice_id | related patterns | verification_status |
|-------------|------------------|---------------------|
| pagination_until_exhausted | pagination_and_batching | source_documented |
| bounded_batch_processing | pagination_and_batching | source_documented |
| checkpoint_before_expensive_step | checkpoint_and_resume | source_documented |
| terminal_dead_letter_handling | dead_letter_queue | source_documented |
| rate_limit_backoff | provider_rate_limit_handling | source_documented |
| quality_gate_before_handoff | quality_gate_after_generation | source_documented |
| specialist_scope_isolation | specialist_subworkflow | source_documented |
| supervisor_does_not_execute_tools | supervisor_pattern | source_documented |
| tool_workflow_permission_boundary | tool_workflow_separation | source_documented |
| manual_edit_resume | human_edit_then_resume | source_documented |
| post_publish_evidence_capture | publication_confirmation | source_documented |
| source_lineage_preservation | source_lineage_preservation | source_documented |
| feedback_to_knowledge_candidate | customer_feedback_to_learning_candidate | source_documented |

## Source references

Practices cite frozen archive bundles:

- `archive/skills/` (methodology)
- `archive/ai-agents/` (agent patterns)
- Catalog metadata crosswalk (no raw workflow body)

## Verification discipline

- `source_documented` by default
- `regression_tested` only with deterministic tests in `tests/test_kb_wpl_01_3b_core_pattern_library.py`
- Never infer `reproduced` from archive claims alone

## Pattern ↔ practice mapping

Each core pattern links `source_practice_ids` to at least one PracticeRecord from the table above.
Patterns may share practices where architectural rules overlap (e.g. resilience domain).
