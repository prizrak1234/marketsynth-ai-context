# Rejected Patterns — KB-WPL-01.3B

Workflows and pattern candidates rejected during core expansion.

## Rejection rules

A catalog workflow **cannot support** a pattern when:

- unresolved critical security finding
- source hash mismatch vs frozen catalog
- missing provenance
- title-only selection without topology evidence
- destructive action without human approval gate
- spend/billing sensitivity (deferred by owner directive)

## Rejected workflow uses

| Workflow ID | Rejection reason |
|-------------|------------------|
| (critical-risk catalog entries) | Unresolved critical finding — excluded from all patterns |
| spend/billing candidates | Owner deferred — not extracted in 01.3B |

## Rejected pattern abstractions

| Proposed abstraction | Rejection reason |
|---------------------|------------------|
| auto_retry_on_unknown_write | Violates idempotency gate — unknown-outcome writes cannot auto-retry |
| supervisor_executes_tools | Violates supervisor boundary — orchestrator must not bypass allowlists |
| feedback_auto_promotes_knowledge | Violates learning boundary — candidate only, no canonical mutation |
| infinite_pagination | Violates termination gate — must have max_pages or cursor end |
| unbounded_batch | Violates batch gate — max_batch_size required |

## Catalog candidate pool

~22 `reusable_pattern_candidate` records remain after pilot (13 sources) and core (17 sources,
with overlap). Remaining candidates reserved for 01.3C evaluation — not rejected permanently.

## Audit trail

Rejections documented in build script source selection (`core_definitions.py`,
`core_source_support_definitions.py`) and manual audit limitations fields.
