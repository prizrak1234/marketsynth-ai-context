# KB-WPL-01.2 — Workflow Catalog Quarantine

| Field | Value |
|-------|-------|
| **Program** | KB-WPL-01.2 |
| **Status** | Repaired via KB-WPL-01.2.1 — pending owner freeze |
| **Schema SoT** | `packages/knowledge/workflow_patterns/0.1.0/` |
| **Blocks** | KB-WPL-01.3 Workflow Pattern Library |

---

## Scope

Static parse of n8n workflow JSON from `Боты в базу знаний.rar` intake. **No execution.**

---

## Source statistics (acceptance run)

| Metric | Count |
|--------|-------|
| JSON discovered | 249 |
| Valid n8n exports | 248 |
| Invalid / malformed | 1 |
| Unique catalog records | 242 |
| Exact duplicates removed | 6 |
| Duplicate families | 3+ |

---

## Parser architecture

`app/knowledge/workflow_catalog/` — read-only modules:

- `parser.py` — JSON-as-data extraction
- `topology.py` — provider-aware + provider-neutral hashes
- `security_scan.py` — structured `SecurityFindingRecord`
- `classifiers.py` — explainable capability + priority (priority in statistics sidecar)
- `deduplication.py` — `DuplicateFamily` grouping
- `serialization.py` — schema validation + artifact writes
- `queries.py` — read-only query layer

---

## Catalog contract

Each record validates against `workflow-template.schema.json` (KB-WPL-01.1).

Defaults:
- `quarantine_status = quarantined`
- `adaptation_status = catalog_only` (or `reusable_pattern_candidate` / `requires_rewrite`)
- No executable body fields
- Credential references metadata-only

---

## Rejected / invalid files

1 JSON file with `json_decode_error` — excluded from catalog, listed in `invalid_files`.

---

## Limitations

- Security scan may produce false positives — acceptable at quarantine stage
- Commercial priority stored in `statistics.json` (not in WorkflowTemplate schema)
- Provider-aware topology hash in statistics sidecar; `topology_hash` field = provider-neutral

---

## Readiness for 01.3

Pattern Library may proceed only from:
- 242 unique quarantined records
- manual audit gate (≥2 sources OR explicit audit)
- no raw workflow bodies

---

## Explicit no-execution confirmation

- No workflow imported to n8n
- No Code node execution
- No shell execution
- No n8n API / SDK
- No network access
- No Connector / MCP / persistence / API / UI

Regression: `uv run pytest tests/test_kb_wpl_01_2_workflow_catalog_quarantine.py -q`
