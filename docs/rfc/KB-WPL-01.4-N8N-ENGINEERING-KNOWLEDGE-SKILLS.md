# KB-WPL-01.4 — n8n Engineering Knowledge Skills

| Field | Value |
|-------|-------|
| **Program** | KB-WPL-01.4 |
| **Status** | **READY** — three candidate non-executable Skills |
| **Depends on** | KB-WPL-01.3C (`frozen_reviewed_library`) |
| **Runtime authorized** | `false` |
| **Production eligible** | `false` |

## 1. Executive verdict

**READY.** Three platform-native engineering Skills consume the frozen Workflow Pattern
Library as read-only knowledge. They design, diagnose, and review n8n workflows without
n8n access, workflow JSON import, deployment, activation, credentials, or external network.

## 2. Deliverables

| Skill ID | Purpose | Package hash |
|----------|---------|--------------|
| `ms.skill.n8n_workflow_architecture` | Architecture specification only | `5af85271…` |
| `ms.skill.n8n_workflow_debugging` | Evidence-backed diagnostic report | `e200b06e…` |
| `ms.skill.n8n_deployment_review` | Manual deployment readiness review | `0ec6874b…` |

## 3. Frozen knowledge bindings

| Artifact | Hash |
|----------|------|
| Library semantic | `1ddd0d033f6028bd5dcf5ee555186c6be0389a96459615b6221348783d9b1883` |
| Schema bundle | `db34d8f1dbd82772d86fc921daa57d7007e748c004bf40b250023d1247823f25` |
| Catalog bundle | `5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa` |
| Pilot bundle | `d2c3f64171bae91fe84708146ab05ff3fde3941f7645abcb006ca9de74a1a284` |
| Core bundle | `b715466982b73f86c11bb05310d72def00a540982baea6ab80882e06b0737fbf` |

## 4. Shared contract: PatternSelectionReference

All three Skills reference patterns via `PatternSelectionReference`:

- `pattern_id`, `library_version`, `library_semantic_hash`
- `selection_reason`, `applicability`, `maturity`
- `runtime_authorized` must be `false`

Unknown patterns, hash mismatches, maturity above `reviewed`, and `runtime_authorized=true`
are rejected.

## 5. Security boundaries

Rejected inputs: API keys, passwords, OAuth tokens, raw credential objects, unsanitized
logs, raw production workflow JSON with secrets.

Allowed: credential reference IDs, provider/node metadata, redacted logs, structural
metadata, hashes.

## 6. Semantic validation

Validation helpers in `app/knowledge/n8n_engineering/` enforce:

- **Architecture:** publication requires approval; write retry requires idempotency;
  LLM-to-API requires structured validation; missing error path blocks readiness.
- **Debugging:** missing evidence limits confidence; sandbox keeps publication/billing
  disabled; no live mutation fields.
- **Deployment:** publication/billing/retry/idempotency gates; activation gate always
  requires `final_manual_action_required=true`.

## 7. Non-goals (explicit)

No n8n API client, Connector, workflow import/generation JSON, deployment, activation,
credential vault, sandbox execution, provider calls, API, UI, DB, MCP, or persistence.

## 8. Verification

```bash
uv run pytest tests/test_kb_wpl_01_3c_pattern_library_freeze.py -q
uv run pytest tests/test_kb_wpl_01_4_n8n_engineering_skills.py -q
uv run ruff check tests/test_kb_wpl_01_4_n8n_engineering_skills.py tests/support app/skills app/knowledge/workflow_patterns app/knowledge/n8n_engineering
```

## 9. Related

- [Engineering Skill Matrix](../skills/ENGINEERING-SKILL-MATRIX.md)
- [Workflow Pattern Library v0.1.0](../architecture/WORKFLOW-PATTERN-LIBRARY-v0.1.0.md)
- Freeze audits: [01.4A](./KB-WPL-01.4A-n8n-workflow-architecture-freeze.md), [01.4B](./KB-WPL-01.4B-n8n-workflow-debugging-freeze.md), [01.4C](./KB-WPL-01.4C-n8n-deployment-review-freeze.md)
