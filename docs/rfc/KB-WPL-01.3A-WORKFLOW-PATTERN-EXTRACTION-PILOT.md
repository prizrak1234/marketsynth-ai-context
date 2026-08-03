# KB-WPL-01.3A — Workflow Pattern Extraction Pilot

| Field | Value |
|-------|-------|
| **Program** | KB-WPL-01.3A |
| **Status** | Frozen after KB-WPL-01.3A.1 lineage hardening; owner accepted controlled expansion |
| **Depends on** | KB-WPL-01.2 FROZEN catalog, KB-WPL-01.1 frozen schemas |
| **Blocks** | KB-WPL-01.3B expansion |

## Objective

Validate pattern extraction methodology on **8 pilot patterns** from **12 source workflows**
before scaling the Workflow Pattern Library.

## Deliverables

- 8 provider-neutral patterns in `patterns/pilot/`
- `pilot_index.json`, `pilot_freeze_manifest.json`, `pilot_audit_records.json`
- Read-only module `app/knowledge/workflow_patterns/`
- 41 regression tests

## Pilot patterns

1. human_approval_before_publication
2. structured_LLM_to_API_request
3. retry_with_idempotency
4. evidence_grounded_generation
5. lead_capture_to_qualification
6. draft_to_human_approval
7. workflow_backup
8. error_workflow_or_recovery

## Boundaries

- maturity=`reviewed` only — not production, not executable
- no raw n8n workflow bodies
- no Connector/Tool activation
- frozen schema bundle hash unchanged
- frozen catalog bundle hash unchanged

## Next

KB-WPL-01.3A.1 lineage hardening ✅ — PracticeRecords + source-support map.

KB-WPL-01.3B — core library expansion ✅ (20 patterns, core_reviewed).
