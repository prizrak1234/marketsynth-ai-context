# Source Support Map — KB-WPL-01.3B

Artifact: `packages/knowledge/workflow_patterns/0.1.0/core_source_support_map.json`

## Purpose

Documents pattern-specific **supporting signals** linking each core pattern to catalog
workflow metadata without embedding raw workflow bodies.

## Signal structure

Each signal identifies:

| Field | Description |
|-------|-------------|
| `pattern_id` | Core pattern supported |
| `source_workflow_id` | Catalog workflow reference |
| `signal_type` | e.g. topology, functional_class, approval_gate |
| `functional_class` | Provider-neutral class from catalog |
| `topology_location` | Segment description (not node IDs) |
| `supported_rule` | Architectural rule validated |
| `confidence` | high / medium |
| `limitations` | Known gaps |
| `evidence_hash` | Deterministic hash of signal metadata |

## Coverage

- **12 patterns** × **2 sources** = 24 primary signal groups
- Multi-pattern workflows documented with per-pattern distinct signals
- `source_support_map_hash`: `93f67e4d4d5442ca599258efe9365660f688ca5494c69d1f01356c30c81ecccc`

## Validation gate

`validate_pattern_source_support()` rules from pilot methodology apply:

- ≥2 distinct catalog sources → supported
- 1 source + matching manual audit → supported (none used in 01.3B)
- 0 sources or critical-risk source → rejected

## Overlap examples

| Workflow | Patterns supported |
|----------|-------------------|
| wf-7227ff0544f5cbd2 | dead_letter_queue, human_edit_then_resume, customer_feedback_to_learning_candidate |
| wf-6114836577421bab | checkpoint_and_resume, provider_rate_limit_handling |
| wf-b2aea5e382059f4b | specialist_subworkflow, source_lineage_preservation, tool_workflow_separation |

Distinct signals per pattern — no source exclusivity.
