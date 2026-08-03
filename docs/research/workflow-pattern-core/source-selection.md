# Core Source Selection — KB-WPL-01.3B

Selected **17 source workflows** (12 new for core expansion; 5 overlap with pilot sources)
from remaining `reusable_pattern_candidate` catalog records after pilot extraction.

## Selection criteria

- `adaptation_status=reusable_pattern_candidate`
- no unresolved critical security finding
- source hash matches frozen catalog (`5389c3a7…`)
- identifiable use case and meaningful topology
- manual audit required per pattern
- rejected workflow cannot support a pattern

## Core pattern ↔ source matrix

| Pattern | Source workflows |
|---------|------------------|
| pagination_and_batching | wf-860ed73d41feb4fd, wf-4795f50628f182d5 |
| checkpoint_and_resume | wf-6114836577421bab, wf-6d6ba3d5c2233d5f |
| dead_letter_queue | wf-4e833d762f583631, wf-7227ff0544f5cbd2 |
| provider_rate_limit_handling | wf-6114836577421bab, wf-b537693ad1b8ee7e |
| quality_gate_after_generation | wf-63b78819a2e5a190, wf-16a4bd5f71833d44 |
| specialist_subworkflow | wf-b2aea5e382059f4b, wf-7c284d78aad2003d |
| supervisor_pattern | wf-6bcda126561b5f72, wf-cb28929d37f1ac61 |
| tool_workflow_separation | wf-7c284d78aad2003d, wf-b2aea5e382059f4b |
| human_edit_then_resume | wf-7227ff0544f5cbd2, wf-c18641f0b4421b0a |
| publication_confirmation | wf-497aa9eee8a759da, wf-9f3a78220a7bfbe3 |
| source_lineage_preservation | wf-63b78819a2e5a190, wf-b2aea5e382059f4b |
| customer_feedback_to_learning_candidate | wf-7227ff0544f5cbd2, wf-770099f8fbf34352 |

## Multi-pattern overlap

Shared workflows (e.g. wf-7227ff0544f5cbd2, wf-6114836577421bab) support multiple patterns
via **distinct support signals** documented in `core_source_support_map.json`. No source
exclusivity is assumed.

## Single-source patterns

All 12 core patterns use **≥2 source workflows**. No single-source patterns in 01.3B.
Future single-source additions must satisfy frozen `SINGLE_SOURCE_POLICY`.

## Rationale

Selection based on catalog `functional_classes`, `topology_signals`, `approval_signal_strength`,
and crosswalk with archive PracticeRecords — not workflow titles alone.
