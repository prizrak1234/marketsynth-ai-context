# SKILL-01.5 — Connector Gateway Interfaces

**Phase:** SKILL-01.5  
**Status:** Complete (2026-07-23)  
**Depends on:** SKILL-01.1 (contracts), RFC-CONN-001, RFC-SKILL-003

---

## Purpose

Define the **canonical contracts, classifications, and policy interfaces** for the Marketsynth Connector Gateway. Skills and Runtime request external capabilities through this layer — never via MCP clients, provider SDKs, or tenant secrets directly.

```
Skill / Runtime
  → ConnectorExecutionRequest
  → Policy evaluation (deny-by-default)
  → Adapter boundary (protocol only in this phase)
  → ConnectorExecutionResult
  → ConnectorEvidenceDescriptor
```

**Not in this phase:** real HTTP, MCP client, credential vault, registry persistence, API, runtime routing.

---

## Architecture boundary

| Layer | Location | SKILL-01.5 role |
|-------|----------|-----------------|
| Connector Gateway | `app/connectors/` | **New** — governing contracts + policy harness |
| Legacy MCP client | `app/mcp/` | **Preserved** — unchanged, not migrated |
| Business tool providers | `app/business_tools/providers/` | **Preserved** — no wrapper migration |

Connector Gateway is the **future** mandatory path for external I/O. Existing XmlRiver/Firecrawl adapters remain in place until a later integration phase.

---

## Module layout

```
app/connectors/
├── __init__.py
├── contracts.py        # Immutable enums + request/result models
├── classifications.py  # Tool action/approval helpers
├── policies.py         # Pure deny-by-default policy evaluation
├── gateway.py          # ConnectorGateway skeleton
├── adapters.py         # Protocol + SyntheticConnectorAdapter only
├── errors.py           # Safe domain errors
├── evidence.py         # Evidence descriptor + hashing/redaction
└── fixtures.py         # Synthetic test descriptors (fixture-only)
```

---

## Connector vs tool

- **Connector** — governed adapter metadata (status, class, health, adapter kind).
- **Connector Tool** — single invocable operation with independent classification.

**Rule:** Connector `active` does **not** enable tools. Each tool requires explicit tenant + project allowlist entry and Skill manifest permission.

Default: `enabled_by_default = false` for every tool.

---

## Tool classification

Required dimensions per `ConnectorToolDefinition`:

| Dimension | Values |
|-----------|--------|
| `action_type` | read, write, delete, admin, publish, execute, billing |
| `side_effect_class` | none, reversible, irreversible, externally_visible, financially_sensitive |
| `data_sensitivity` | public, tenant_internal, personal, confidential, credential_adjacent |
| `approval_class` | none, user_confirmation, owner_approval, elevated_approval |
| `idempotency` | guaranteed, supported_by_key, provider_best_effort, unknown, not_idempotent |

Flags: `billing_sensitive`, `publication_sensitive`, `destructive`, `enabled_by_default`.

---

## Credential boundary

`CredentialBindingReference` is **metadata only**:

- `binding_id`, `tenant_id`, `provider`, `connector_id`, `scope_names`, `status`, `expires_at`, `rotated_at`, `project_allowlist`, `metadata_only=true`

**Forbidden in binding:** access tokens, refresh tokens, API keys, client secrets, passwords, private keys.

- Credentials are **tenant-scoped** (Owner Decision 002).
- Projects **reference** tenant bindings; they do not own secrets.
- Skills never receive credential material.
- Adapters receive opaque binding references from a future secure credential service (not implemented).

---

## Request / result contracts

### ConnectorExecutionRequest

Mandatory: `request_id`, `correlation_id`, `tenant_id`, `project_id`, `actor_id`, `connector_id`, `connector_version`, `tool_id`, `input_payload`, `requested_at`.

Optional: `skill_id`, `skill_version`, `credential_binding_reference`, `approval_reference`, `evidence_context`, `budget_context`, `idempotency_key`, `timeout_policy`, `retry_policy`, `dry_run`, `skill_allowed_tools`.

Rules:

- No secrets in `input_payload` (secret-like keys rejected by policy).
- Connector-wide generic execution forbidden — `tool_id` is mandatory.
- Serializable only — no runtime client objects.

### ConnectorExecutionResult

Statuses: `succeeded`, `failed`, `rejected_by_policy`, `approval_required`, `unavailable`, `timed_out`, `rate_limited`, `duplicate_prevented`, `unknown_outcome`.

Includes normalized `safe_provider_metadata`, optional `evidence_descriptor`, skill identity preserved.

---

## Policy evaluation

`evaluate_connector_request(...)` — pure function, deny-by-default.

Outcomes: `allow`, `deny`, `require_approval`, `require_additional_context`, `defer`, `unavailable`.

Checks (20): connector status, tool enabled state, tenant visibility, project allowlist, credential binding, tool-level allowlist, action classification, approval, billing/publication/destructive sensitivity, tenant scope, skill tool permission, runtime compatibility, budget, rate/idempotency, evidence requirements, dry-run, health state.

Unknown policy data → **deny**, never allow.

---

## Skill intersection rule

```
Skill manifest allowed_tools
  ∩ Registry policy
  ∩ Connector tool allowlist (tenant + project)
  ∩ Approval state
  = effective permission
```

No single layer grants access alone.

Frozen `ms.skill.market_validation` has `allowed_tools: []` → **all connector requests denied**.

---

## Approval policy

| Tool class | Default |
|------------|---------|
| Read-only, no side effect | May allow without approval if all other checks pass |
| Write | Require approval |
| Delete / Admin | Require elevated approval |
| Publish | Require approval; route through native publication contour where authoritative |
| Billing-sensitive | Require approval + budget context |
| Advertising spend | **Deny by default** (current phase) |
| Telegram MCP | **Rejected** |

---

## Evidence descriptor

`ConnectorEvidenceDescriptor` — descriptor only, no persistence in SKILL-01.5.

Fields include: `evidence_id`, `request_id`, connector/tool/skill identity, tenant/project, action/side-effect classes, hashes (`input_hash`, `output_hash`, `provider_metadata_hash`), timestamps, `result_status`, `lineage_parent_ids`.

Hashes are deterministic (SHA-256 over canonical JSON).

---

## Cost / budget

`ConnectorCostEstimate` — metadata only (currency, min/max, unit, confidence).

`BudgetPolicy` — tenant/project/request limits, approval threshold, `deny_above_limit`.

Unknown cost for billing-sensitive tools → **not auto-allowed**.

---

## Rate / idempotency

`RetryPolicy` metadata: `max_attempts`, `retryable_statuses`, backoff, duplicate side-effect risk.

Policy rules:

- Non-idempotent write → no auto-retry
- Unknown-outcome write → no auto-retry
- Idempotent read may declare retry policy

No real retry loop in this phase.

---

## Adapter protocol

`ConnectorAdapterProtocol`:

- `describe_connector()`
- `list_tools()`
- `validate_configuration()`
- `health_check()`
- `execute_tool(request)`

SKILL-01.5:

- `SyntheticConnectorAdapter` — in-memory test adapter with invocation counter
- `ProductionConnectorAdapterStub` — raises `NotImplementedError`
- No network clients, SDKs, or credentials

Gateway evaluates policy **before** adapter invocation. Denied and approval-required requests never call the adapter.

---

## Native Telegram boundary

- `connector.native.telegram_publication` — authoritative internal publication metadata (`is_native_authoritative=true`, `is_mcp=false`)
- `fixture.connector.telegram_mcp_rejected` — rejected MCP fixture (`status=rejected`, `is_mcp=true`)

Native Telegram publication logic in production modules is **not** replaced or wrapped in this phase.

---

## Synthetic fixtures (test-only)

| Fixture | Class | Tool | Policy posture |
|---------|-------|------|----------------|
| `fixture.connector.research_read` | research | `research.read` | read-only, allow with allowlists |
| `fixture.connector.content_generation` | content_generation | `content.generate` | billing, approval required |
| `fixture.connector.publication` | publication | `publication.publish` | publish, approval required |
| `fixture.connector.advertising` | advertising | `advertising.spend` | denied by default |
| `connector.native.telegram_publication` | publication | `telegram.publish_native` | native authoritative metadata |

---

## Limitations

- No Connector Registry persistence
- No credential vault / OAuth
- No real HTTP or MCP client
- No API endpoints or frontend
- No runtime execution integration
- No Evidence persistence
- No billing ledger

---

## Non-goals

- Migrating `app/mcp/` adapters into Connector Gateway
- Firecrawl / XmlRiver / Higgsfield / Telegram MCP / Ads / CRM invocation
- CWF.1 / CWF.1a behavior changes

---

## Future connector runtime integration

Later phases (post SKILL-01.8 freeze):

1. Connector Registry persistence + lifecycle transitions
2. Secure credential service injection at adapter boundary
3. Runtime routing from Skill execution → Connector Gateway
4. Controlled passthrough to existing native adapters (XmlRiver, Firecrawl, native Telegram)
5. Evidence persistence and audit report aggregation (SKILL-01.6)

---

## Verification

```bash
uv run pytest \
  tests/test_skill_01_0_market_validation_package.py \
  tests/test_skill_01_0_freeze_audit.py \
  tests/test_skill_01_1_contracts.py \
  tests/test_skill_01_2_package_validator.py \
  tests/test_skill_01_3_registry_read_models.py \
  tests/test_skill_01_4_quarantine_import_adapter.py \
  tests/test_skill_01_5_connector_gateway_interfaces.py \
  -q

uv run ruff check app/connectors tests/test_skill_01_5_connector_gateway_interfaces.py
```

**Result (2026-07-23):** 203 passed, 3 skipped; ruff clean on connector modules.

---

## Related documents

- [RFC-CONN-001](../rfc/RFC-CONN-001-connector-gateway-and-private-registry.md)
- [RFC-SKILL-003](../rfc/RFC-SKILL-003-skill-security-and-trust-boundary.md)
- [SKILL-CONN-glossary](../rfc/SKILL-CONN-glossary.md)
- [SKILL-01 Foundation Plan](../rfc/SKILL-01-FOUNDATION-IMPLEMENTATION-PLAN.md)
