# Workflow Pattern Catalog

Canonical index of Marketsynth Workflow Patterns at `packages/knowledge/workflow_patterns/0.1.0/`.

## Library tiers

| Tier | Path | Count | Maturity cap | Status |
|------|------|-------|--------------|--------|
| Pilot (frozen) | `patterns/pilot/` | 8 | reviewed | FROZEN (01.3A.1) |
| Core (frozen) | `patterns/core/` | 12 | reviewed | FROZEN (01.3B) |
| **Library** | `library_index.json` | **20** | reviewed | **frozen_reviewed_library (01.3C)** |

No pattern grants execution permission. `runtime_authorized=false`.

## Pilot patterns (immutable)

| pattern_id | Problem domain |
|------------|----------------|
| human_approval_before_publication | Publication gate |
| structured_LLM_to_API_request | LLM → typed API |
| retry_with_idempotency | Resilience |
| evidence_grounded_generation | RAG / evidence |
| lead_capture_to_qualification | CRM intake |
| draft_to_human_approval | Draft review |
| workflow_backup | Operational safety |
| error_workflow_or_recovery | Error path |

## Core patterns (01.3B)

### Control / review

| pattern_id | Summary |
|------------|---------|
| human_edit_then_resume | Authoritative human edit before continuation |
| publication_confirmation | Post-publish evidence + confirmation gate |

### Resilience

| pattern_id | Summary |
|------------|---------|
| pagination_and_batching | Bounded page/batch traversal |
| checkpoint_and_resume | Persist state before expensive steps |
| dead_letter_queue | Terminal handling after retry exhaustion |
| provider_rate_limit_handling | Backoff on provider rate limits |

### AI / agents

| pattern_id | Summary |
|------------|---------|
| quality_gate_after_generation | Block invalid LLM output before handoff |
| specialist_subworkflow | Scoped sub-workflow for one capability |
| supervisor_pattern | Orchestrator without direct tool execution |
| tool_workflow_separation | Permission boundary between tools and flows |

### Data flow

| pattern_id | Summary |
|------------|---------|
| source_lineage_preservation | Carry source refs through transforms |

### Marketing / learning

| pattern_id | Summary |
|------------|---------|
| customer_feedback_to_learning_candidate | Feedback → draft knowledge candidate only |

## Governance artifacts

| Artifact | Purpose |
|----------|---------|
| `core_freeze_manifest.json` | Deterministic bundle hash + per-pattern hashes |
| `core_source_support_map.json` | Pattern ↔ catalog workflow support signals |
| `core_audit_records.json` | Manual audit lineage (`owner_review_required=true`) |
| `practices/core/*.json` | Archive-backed PracticeRecords |
| `SINGLE_SOURCE_POLICY` | Frozen policy in `contracts.py` |

## Deferred (not in 01.3B)

Spend/billing, destructive activation, `platform_adapted` maturity, runtime/API/DB/Connector.
See `docs/research/workflow-pattern-core/deferred-patterns.md`.

## Related docs

- [Extraction methodology](./WORKFLOW-PATTERN-EXTRACTION-METHODOLOGY.md)
- [KB-WPL-01.3B RFC](../rfc/KB-WPL-01.3B-CORE-PATTERN-LIBRARY.md)
- [Core research notes](../research/workflow-pattern-core/)
