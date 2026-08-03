# Source Overlap Matrix — KB-WPL-01.3C

Artifact: `packages/knowledge/workflow_patterns/0.1.0/source_overlap_matrix.json`

## Policy

Multi-pattern use of one catalog workflow is **allowed** when:
- each pattern cites distinct `supported_rule` values
- support signals are pattern-specific
- limitations document shared-source dependence

No source exclusivity requirement.

## Overlap summary

`overlap_count`: workflows supporting >1 pattern (see manifest `overlap_matrix_hash`).

## Example overlaps

| source_workflow_id | patterns | independence |
|--------------------|----------|--------------|
| wf-7227ff0544f5cbd2 | dead_letter_queue, human_edit_then_resume, customer_feedback_to_learning_candidate | pattern_specific_signals |
| wf-6114836577421bab | checkpoint_and_resume, provider_rate_limit_handling | pattern_specific_signals |
| wf-b2aea5e382059f4b | specialist_subworkflow, source_lineage_preservation, tool_workflow_separation | pattern_specific_signals |

## Independence assessment values

- `single_pattern` — workflow supports one pattern only
- `pattern_specific_signals` — multiple patterns, distinct rules per pattern
- `shared_rule_overlap` — same rule reused (documented in limitations)

## Audit rule

Exact duplicate workflows count as one architectural source for diversity assessment.
Two-source patterns must use materially distinct support signals, not copied evidence.
