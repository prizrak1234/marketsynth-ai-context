# Workflow Pattern Extraction Methodology

## 1. Pilot scope (01.3A)

Extract **one architectural problem per pattern** from quarantined catalog metadata.
Pilot limit: **6–8 patterns**, **8–12 source workflows**.

## 2. Source selection

1. Filter `reusable_pattern_candidate` records with `manual_audit_required=true`.
2. Exclude unresolved critical security findings.
3. Match structural signals: approval, RAG, retry, backup, lead qualification.
4. Prefer ≥2 supporting workflows; single-source requires manual audit record.
5. Document selection rationale — never title-only selection.

## 3. Manual audit method

Each pattern receives `audit-{pattern_id}` record with:

- `reviewer_role`, `review_method` (no fabricated human names)
- `reviewed_source_ids`, `reviewed_practice_ids`
- `audit_hash`, `owner_review_required=true`
- decision=`approved_for_pilot` (not production)

## 3.1 Practice lineage (01.3A.1)

Each pattern links to archive-backed **PracticeRecord** artifacts in `practices/pilot/`.
Placeholder `source_practice_ids` are forbidden after hardening.

## 3.2 Source support map

`pilot_source_support_map.json` documents pattern-specific `supporting_signals`:

- which workflow, node/functional class, topology segment
- which architectural rule is supported
- deterministic `evidence_hash` per signal

**Multi-pattern overlap:** one workflow may support multiple patterns when each pattern cites
distinct signals (no source exclusivity).

## 3.3 Single-source policy (frozen for 01.3B)

See `SINGLE_SOURCE_POLICY` in `app/knowledge/workflow_patterns/contracts.py`.

## 4. Abstraction rules

- Pattern = architectural abstraction, not workflow copy
- Main flow uses functional classes (`publication_target`, `LLM_provider`, …)
- Provider names only in `implementation_variants`
- No credentials, node IDs, expressions, or raw JSON

## 5. Source support gate

`validate_pattern_source_support(pattern, catalog, audits)`:

- ≥2 distinct catalog sources → supported
- 1 source + matching manual audit → supported
- 0 sources or critical-risk source → rejected

## 6. Approval / evidence / idempotency

- Publication patterns: `publication_approval_required=true`, no auto approval
- Evidence required for external actions
- Retry patterns: idempotency required, no unknown-outcome auto-retry on writes
- RAG patterns: source references + injection boundary documented

## 7. Quality gates

Mandatory gates before `maturity=reviewed`:

schema_valid, source_support_valid, provider_neutral, no_credentials,
approval_boundary_valid, evidence_boundary_valid, tenant_boundary_valid,
idempotency_valid, error_path_present, limitations_documented, manual_review_complete

## 8. Scale-up criteria for 01.3B

Proceed when:

- owner accepts pilot patterns as grounded (not over-abstract) ✅
- source support gate proven on 8 patterns ✅
- no schema changes required ✅
- duplicate-family canonical workflows prioritized for expansion ✅

**KB-WPL-01.3B complete:** 12 core patterns added (20 total). See
[WORKFLOW-PATTERN-CATALOG.md](./WORKFLOW-PATTERN-CATALOG.md).

## 8.1 Core library scope (01.3B)

- Patterns in `patterns/core/` — maturity `reviewed` only
- `core_source_support_map.json` + `core_audit_records.json` + `practices/core/`
- Pilot artifacts immutable; core bundle hash independent of pilot semantic hash
- Build: `uv run python scripts/kb_wpl_01_3b_core.py`

## 9. Non-execution boundary

No workflow execution, n8n import, network, Connector, API, UI, DB, or MCP in extraction path.

## 10. Library freeze (01.3C)

**KB-WPL-01.3C complete:** 20 patterns frozen at `frozen_reviewed_library`.
See [WORKFLOW-PATTERN-LIBRARY-v0.1.0.md](./WORKFLOW-PATTERN-LIBRARY-v0.1.0.md).

- Build: `uv run python scripts/kb_wpl_01_3c_freeze.py`
- `runtime_authorized=false`, `production_eligible=false`
- No new patterns in freeze phase
- Maturity ceiling remains `reviewed`
