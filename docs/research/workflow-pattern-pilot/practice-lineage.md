# Practice lineage — KB-WPL-01.3A.1

## PracticeRecords created (11)

| practice_id | verification_status | related patterns |
|-------------|---------------------|------------------|
| human_approval_before_write_or_publication | source_documented | human_approval, draft_to_approval |
| structured_output_before_API_call | source_documented | structured_LLM |
| idempotency_before_retry | regression_tested | retry_with_idempotency |
| unknown_outcome_write_no_auto_retry | regression_tested | retry_with_idempotency |
| evidence_grounded_generation | regression_tested | evidence_grounded_generation |
| prompt_injection_boundary | regression_tested | evidence_grounded_generation |
| lead_qualification_boundary | source_documented | lead_capture |
| draft_review_resume | source_documented | draft_to_human_approval |
| workflow_backup_and_source_control | source_documented | workflow_backup |
| explicit_error_workflow | source_documented | error_workflow_or_recovery |
| recovery_and_terminal_failure_path | regression_tested | error_workflow_or_recovery |

## Archive sources

| Archive | Relative path | Used for |
|---------|---------------|----------|
| arc-skills-dlya-peredachi | n8n-knowledge-base/references/methodology.md | approval, retry, error, backup, lead |
| arc-skills-dlya-peredachi | n8n-knowledge-base/references/ai-agents.md | structured output, RAG, injection |
| arc-bots-knowledge-rar | Стандарт/Скиллы/06_QUALITY_GATE.md | human review gates |

Archive wording such as «✅ Подтверждено в проде» in source files does **not** auto-map to
`verification_status=reproduced` — only `source_documented` or `regression_tested` where
current pytest invariants exercise the rule.

## Pattern → practice mapping

See `packages/knowledge/workflow_patterns/0.1.0/pilot_practice_index.json` and each
pattern's `source_practice_ids` field.
