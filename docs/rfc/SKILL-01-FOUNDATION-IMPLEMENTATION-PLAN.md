# SKILL-01 — Foundation Implementation Plan

**Phase:** SKILL-01 Foundation  
**Status:** Approved for implementation (post SKILL-00.9)  
**Approved by Owner:** 2026-07-23  
**Depends on:** Accepted RFC-SKILL-001..003, RFC-CONN-001, [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md)

---

## Strategic principle — top-down, scenario-driven

Marketsynth builds an **AI marketing agency**, not an abstract Skill platform.

**Rejected approach (bottom-up):**

```
Registry → Validator → Gateway → Skill (maybe used later)
```

**Accepted approach (top-down):**

```
MS-SKILL-001 Market Validation (driver)
  → derive Contracts + Validator + Registry from real package
  → MS-SKILL-002 Research, MS-SKILL-003 Competitor Analysis (extend)
  → Connector Gateway stub where driver Skill needs tools
  → Runtime (SKILL-02+, only after foundation freeze)
```

Each infrastructure layer MUST be justified by a **commercial P0 Skill skeleton**, starting with Market Validation (maps to audit ID **MS-SKILL-005**; owner commercial ID **MS-SKILL-001**).

| Owner commercial ID | Audit registry ID | Name |
|--------------------|-------------------|------|
| MS-SKILL-001 | MS-SKILL-005 | Market Validation |
| MS-SKILL-002 | MS-SKILL-002 | Market Research |
| MS-SKILL-003 | MS-SKILL-003 | Competitor Analysis |

---

## Scope boundary

### In scope (SKILL-01)

| Item | Deliverable |
|------|-------------|
| Skill contracts | Types in `contracts.py` — derived from MS-SKILL-001 skeleton |
| Package manifest schema | JSON Schema + MSP layout |
| Package validator | CLI static validation |
| Quarantine import adapter | External Agent Skills → quarantine record only |
| Registry read model | File/in-memory; MS-SKILL-001 registered as `candidate` |
| Audit report schema | JSON for quarantine → audited |
| Connector Gateway interfaces | Abstract gateway + XmlRiver/Firecrawl passthrough |
| Market Validation Skill skeleton | MSP package for BIV/Launch Pack contracts |
| Lineage metadata | Nullable fields / types for `skill_id` + `skill_version` |
| Freeze audit | Regression checklist + owner sign-off gate |

### Out of scope (SKILL-01)

- Skill execution engine / dynamic loader
- LLM activation of Skill packages
- External GitHub installation / marketplace
- Tenant upload UI
- Skill composer / automatic routing by registry
- Higgsfield connection
- Playwright integration
- Telegram MCP
- Ads connectors
- CRM connectors
- Database migrations (unless trivial nullable lineage — owner approval per slice)
- API endpoints
- Frontend changes

---

## Implementation phases

Each sub-phase is **implemented, tested, and frozen** before the next begins.

### SKILL-01.0 — Driver skeleton (first)

**Status:** ✅ **FROZEN** (2026-07-23) — [freeze audit](SKILL-01-0-freeze-audit.md)

**Deliverable:** `packages/skills/ms.skill.market_validation/` MSP skeleton.

### SKILL-01.1 — Canonical contracts

**Status:** ✅ **Complete** (2026-07-23)

**Deliverable:** Skill package types in `app/schemas/contracts.py`; field mapping in [skill-contract-field-mapping.md](../skills/skill-contract-field-mapping.md); tests `tests/test_skill_01_1_contracts.py`.

- `SKILL.md` — methodology stub aligned with BIV / CWF.1
- `manifest.yaml` — full required fields; `status: candidate`; read-only tools only
- `schemas/` — input/output aligned with existing BIV contracts
- `tests/` — placeholder eval cases (verdict blocked without evidence)

**Exit criteria:** Skeleton defines what contracts and validator must support. Owner confirms commercial shape.

**Completed artifacts:**

- Package: `packages/skills/ms.skill.market_validation/`
- Docs: `docs/skills/ms.skill.market_validation.md`
- Tests: `tests/test_skill_01_0_market_validation_package.py` (24 passed)
- Package root README: `packages/skills/README.md`

**Not completed (by design):** SKILL-01.2–01.8 remain pending at time of 01.0 freeze.

---

### SKILL-01.2 — Manifest and Package Validator

**Status:** ✅ **Complete** (2026-07-23)

**Deliverable:** `app/skills/` production validator + CLI; docs [SKILL-01.2-manifest-package-validator.md](../skills/SKILL-01.2-manifest-package-validator.md); tests `tests/test_skill_01_2_package_validator.py` (35 cases).

- PyYAML + jsonschema as **direct** production dependencies
- Safe YAML parsing → `SkillManifest` domain contracts
- Package structure, path safety, JSON Schema, security invariants
- Deterministic hash (matches freeze audit)
- `tests/support/skill_package_validation.py` deprecated for validation

**Exit criteria:** Frozen package passes production validation; negative security tests pass; SKILL-01.0/01.1 tests remain green.

---

### SKILL-01.3 — Registry Read Models

**Status:** ✅ **Complete** (2026-07-23)

**Deliverable:** `app/skills/registry_*.py`; docs [SKILL-01.3-registry-read-models.md](../skills/SKILL-01.3-registry-read-models.md); tests `tests/test_skill_01_3_registry_read_models.py` (35 cases).

- Immutable read models + validation report projection
- Deterministic snapshot + queries + tenant visibility
- Eligibility derived without mutation; conflict detection only

**Exit criteria:** Frozen package projects correctly; no candidate becomes approved/active; no persistence/API.

---

### SKILL-01.4 — Quarantine Import Adapter

**Status:** ✅ **Complete** (2026-07-23)

**Deliverable:** `app/skills/quarantine_*.py`; fixture `tests/fixtures/skills/quarantine/valid_external/`; docs [SKILL-01.4-quarantine-import-adapter.md](../skills/SKILL-01.4-quarantine-import-adapter.md); tests `tests/test_skill_01_4_quarantine_import_adapter.py` (42 cases).

- Local directory import only (no network/git)
- Isolated quarantine workspace + static inspection
- Production validator `quarantine_import` mode
- Provenance with declared vs verified separation
- Effective status always `quarantined`; never tenant visible / production eligible

**Exit criteria:** External package quarantined safely; conflicts detected; no installation/activation.

---

### SKILL-01.5 — Connector Gateway Interfaces

**Status:** ✅ **Complete** (2026-07-23)

**Deliverable:** `app/connectors/` (contracts, classifications, policies, gateway, adapters, errors, evidence, fixtures); docs [SKILL-01.5-connector-gateway-interfaces.md](../skills/SKILL-01.5-connector-gateway-interfaces.md); tests `tests/test_skill_01_5_connector_gateway_interfaces.py` (45 cases).

- Immutable Connector + Tool contracts with independent tool classification
- Deny-by-default pure policy evaluation (20 checks)
- Credential binding metadata only — no secrets
- Skill ∩ Registry ∩ Tenant ∩ Project ∩ Approval intersection rule
- Frozen `ms.skill.market_validation` (`allowed_tools: []`) denies all connector access
- `ConnectorGateway` policy harness + `SyntheticConnectorAdapter` only
- Native Telegram boundary metadata distinct from rejected Telegram MCP
- Existing `app/mcp/` and business tool providers **unchanged**

**Exit criteria:** Interface tests pass; no real external connections; no MCP client; no credential storage; no API/runtime integration.

---

### SKILL-01.6 — Unified Audit Report Schema

**Status:** ✅ **Complete** (2026-07-23)

**Deliverable:** `app/audit/` (contracts, classifications, adapters, aggregator, readiness, serialization, redaction, fixtures); docs [SKILL-01.6-unified-audit-report.md](../skills/SKILL-01.6-unified-audit-report.md); tests `tests/test_skill_01_6_unified_audit_report.py` (48 cases).

- Canonical `UnifiedAuditReport` + `AuditFinding` with preserved `source_system` / `source_code`
- Pure adapters from package validation, quarantine import, registry conflicts/projection, connector policy/evidence
- Centralized severity normalization and blocking rules (approval ≠ security error)
- Diagnostic `decision_readiness` without lifecycle mutation or activation
- Deterministic aggregation, deduplication, and SHA-256 report hash
- Evidence reference mapping without duplicate persistence
- Secret/path redaction; no approve/activate fields

**Exit criteria:** All source findings normalize into one report; tests pass; no DB/API/UI.

---

### SKILL-01.7 — Lineage Preparation

**Status:** ✅ **Complete** (2026-07-23)

**Deliverable:** `app/lineage/` (contracts, identity, builders, validators, serialization, mappings, fixtures); docs [SKILL-01.7-lineage-preparation.md](../skills/SKILL-01.7-lineage-preparation.md); tests `tests/test_skill_01_7_lineage_preparation.py` (49 cases).

- Immutable lineage node/edge contracts with finite enums
- Deterministic node identity rules (skill, validation, quarantine, registry, connector, audit, evidence)
- Pure builders for package → validation → quarantine → registry → connector → audit chains
- Continuity validation with tenant boundaries and lifecycle semantics guards
- Skill/Connector/Audit execution lineage descriptors (contracts only)
- Evidence mapping to existing `KnowledgeEvidenceRef` — no duplicate persistence
- Deterministic graph serialization and SHA-256 graph hash
- `combine_lineage_graphs()` with conflict and cross-tenant rejection

**Exit criteria:** All lineage chain tests pass; no DB/API/UI/runtime integration; CWF.1/CWF.1a unchanged.

---

### SKILL-01.8 — Foundation Freeze Audit

**Status:** ✅ **Complete** (2026-07-23) — **Verdict: CONDITIONALLY READY**

**Deliverable:** `app/foundation/freeze_fixture.py`; `tests/test_skill_01_8_foundation_invariants.py` (61 cases); docs [SKILL-01-FOUNDATION-FREEZE-AUDIT.md](SKILL-01-FOUNDATION-FREEZE-AUDIT.md), [SKILL-01-FREEZE-MANIFEST.md](SKILL-01-FREEZE-MANIFEST.md).

- Cross-layer architecture, security, tenant, approval, Evidence, lineage audit
- 20 architectural invariants mapped to tests
- Integrated in-memory freeze contour (package → audit → lineage)
- Required patch: dedupe duplicate `SkillLifecycleStatus` in `contracts.py`
- Full SKILL-01 regression: 361 passed, 3 skipped

**Exit criteria:** Audit verdict issued; no security/tenant/approval blockers; owner acceptance pending for full freeze close.

**Freeze checklist:**

- [x] All SKILL-01.0–01.7 deliverables complete
- [x] [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md) reflected in code contracts
- [x] No execution engine shipped
- [x] No MCP installed
- [x] Foundation modules do not modify CWF.1 / CWF.1a
- [ ] Owner freeze sign-off (CONDITIONALLY READY)

**Exit criteria (program):** Owner accepts SKILL-01 freeze → unlock SKILL-02 Native Skills.

---

## Testing strategy

| Layer | Test type |
|-------|-----------|
| MS-SKILL-001 skeleton | Fixture package committed; validator golden tests |
| Contracts | Unit tests for lifecycle enums and transitions |
| Registry | Lookup/filter tests with tenant scope |
| Import adapter | Quarantine-only integration test |
| Gateway stub | Passthrough mock tests; deny undeclared tools |
| Audit schema | JSON schema validation tests |

No live external API calls required for SKILL-01 freeze.

---

## After SKILL-01

Per [SKILL-ROADMAP](SKILL-ROADMAP.md):

1. **SKILL-02** — Native Skills: MS-SKILL-001 execution against BIV (minimal runtime)
2. Extend MS-SKILL-002, MS-SKILL-003 packages using frozen contracts
3. **SKILL-03** — Connector Runtime hardening (tenant credentials, gateway enforcement)
4. **SKILL-04** — Tenant-private Skills (self-serve path per Owner Decision 001)
5. **SKILL-05** — Marketplace (future only — no implementation planned)

---

## Related documents

- [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md)
- [SKILL-ROADMAP](SKILL-ROADMAP.md)
- [RFC-SKILL-001](RFC-SKILL-001-skill-registry-and-lifecycle.md)
- [RFC-SKILL-002](RFC-SKILL-002-skill-package-format.md)
- [RFC-CONN-001](RFC-CONN-001-connector-gateway-and-private-registry.md)
- [SKILL-R0.2 summary](SKILL-R0.2-rfc-drafting-summary.md)
