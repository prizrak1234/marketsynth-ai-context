# KB-WPL-01.1 — Shared Knowledge Contracts

| Field | Value |
|-------|-------|
| **Program** | KB-WPL-01.1 |
| **Status** | Frozen (schema bundle) |
| **Depends on** | KB-WPL-01.0 Archive Intake Freeze (accepted) |
| **Blocks** | KB-WPL-01.2 Workflow Catalog Quarantine |

---

## Objective

Versioned JSON Schema contracts for external knowledge ingestion into the Workflow Pattern Library architecture:

```
Knowledge Core → Workflow Pattern Library → Capabilities → Native Skills → Connector Gateway
```

This phase creates **schemas only** — no parser, no pattern extraction, no persistence.

---

## Canonical location

```
packages/knowledge/workflow_patterns/0.1.0/
```

**URI base:** `https://schemas.marketsynth.ai/workflow-patterns/0.1.0/`  
Identity only — no HTTP resolution.

---

## Schemas (16)

| Schema | Role |
|--------|------|
| `knowledge-artifact` | Generic knowledge artifact envelope |
| `source-reference` | Archive file reference with hash |
| `workflow-template` | Quarantined n8n export **metadata only** |
| `workflow-pattern` | Provider-neutral reusable architecture |
| `workflow-pattern-step` | Pattern step |
| `workflow-pattern-edge` | Pattern edge |
| `capability-reference` | Capability binding |
| `connector-requirement` | Future connector need |
| `tool-requirement` | Future tool need |
| `practice-record` | Engineering practice |
| `error-pattern` | Failure pattern |
| `quality-gate` | QA gate |
| `security-finding` | Redacted security finding |
| `provider-constraint` | Version-scoped provider claim |
| `provenance` | Mandatory lineage |
| `pattern-audit-report` | Audit report envelope |

---

## Hard constraints

1. **WorkflowTemplate** — no `nodes`, `connections`, or executable body fields.
2. **WorkflowPattern** — no raw n8n JSON; provider-neutral by default.
3. **Credential references** — metadata (`credential_id_ref`) only; no secret values.
4. **Maturity** — no `active` / `executable` values.
5. **Provider claims** — require `documented_version`, `documented_at`, `requires_reverification`.
6. **Publication patterns** — require `publication_approval_required`.
7. **Retry patterns** — require idempotency policy; unknown-outcome writes must not auto-retry.
8. **Destructive patterns** — `auto_approval_allowed` must be false.
9. **Provenance** — mandatory on all primary artifacts.
10. **Tenant scope** — mandatory on tenant-bound artifacts.

---

## Semantic validation (tests)

JSON Schema validates structure; `tests/support/wpl_schema_validation.py` enforces business rules listed above.

---

## Hashing

- **File hashes:** SHA-256 of each `.schema.json` file bytes.
- **Bundle hash:** SHA-256 of sorted `file_hashes` JSON (deterministic).
- **Semantic manifest hash:** excludes `generated_at`.

Regression: `uv run pytest tests/test_kb_wpl_01_1_shared_knowledge_contracts.py -q`

---

## Explicit non-goals (this phase)

- Workflow catalog parser
- Pattern extraction from 242 unique workflows
- Native Skills changes
- Discovery module
- Persistence / API / UI
- Script or workflow execution

---

## Next phase

**KB-WPL-01.2** — statically parse 248 valid n8n exports into metadata-only catalog using these contracts as SoT.
