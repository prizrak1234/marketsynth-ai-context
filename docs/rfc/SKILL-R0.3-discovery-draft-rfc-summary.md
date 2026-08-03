# SKILL-R0.3 — Discovery & Draft Generation RFC Summary

**Phase:** SKILL-R0.3 — RFC Drafting (documentation only)  
**Date:** 2026-07-23  
**Status:** Complete  
**RFC:** [RFC-SKILL-004 — Skill Discovery and Draft Generation](RFC-SKILL-004-skill-discovery-and-draft-generation.md) (**Draft** — pending owner review)

---

## 1. RFC created

| Document | Status |
|----------|--------|
| [RFC-SKILL-004](RFC-SKILL-004-skill-discovery-and-draft-generation.md) | **Draft** |

Not marked Accepted — requires owner review per SKILL-00.9 pattern.

---

## 2. Discovery architecture

**Skill Finder (read-only):**

```
Capability Analyzer → Internal Skill Finder → External Candidate Discovery
  → Gap Analyzer → Recommendation Report
```

**Key properties:**

- Recommends; never installs
- No permissions granted
- No external code execution
- Explainable ranking (similarity alone insufficient)
- Active internal Skills prioritized over external popularity

---

## 3. Draft Generator architecture

**Separate contour (quarantine-only):**

```
Approved Gap → Draft Generator → Static Validator → Duplicate Check
  → Quarantine → Audit → Owner Decision
```

**Allowed generated statuses:** `candidate`, `quarantined` only.

**Default permissions:** none — empty `allowed_tools`, scripts disabled, network deny.

---

## 4. Hard boundaries

| Rule | Enforcement |
|------|-------------|
| Discovery read-only | No install, no execute, no permissions |
| Draft never activates | Status cap at quarantined |
| External install | Rejected (marketplace, Smithery trust root) |
| Auto-composition | Rejected in this RFC |
| Combined Discovery+Generator agent | Rejected |
| Marketplace | Future only (SKILL-05) |

---

## 5. Security findings (architecture)

- Malicious SKILL.md → quarantine + static scan + human audit
- Ranking manipulation → explainable factors + hard filters
- Cross-tenant leakage → tenant scope on Discovery output
- Permission escalation → deny-by-default generated manifests
- Provenance falsification → content hash + audit records (signing OQ-D005)

Aligns with [ARCHITECTURAL-INVARIANTS](ARCHITECTURAL-INVARIANTS.md) invariants 1, 14, 15, 16.

---

## 6. Tenant model

- Discovery: tenant sees global + own tenant_private Skills
- External candidates: metadata only — no tenant data embedded
- Generated tenant-private drafts: visible only in originating tenant
- Global promotion: platform audit mandatory (OD-001)

---

## 7. Human gates

Discovery: no approval required (read-only).

Draft / lifecycle: 9 human decision gates documented (adaptation, audit, permissions, connectors, tenant activation, global promotion, elevated tools, scripts, publication/billing).

---

## 8. Roadmap changes

Updated [SKILL-ROADMAP](SKILL-ROADMAP.md):

| Phase | Addition |
|-------|----------|
| **SKILL-02.5** | Skill Discovery (read-only) |
| **SKILL-04** | Tenant Draft Generation (quarantine-only) added to Tenant Skills phase |

Draft Generation **not** placed in SKILL-01.

---

## 9. Open questions (RFC-SKILL-004)

OQ-D001..D011 — ranking benchmarks, cost estimation, tenant quotas, duplicate thresholds, provenance signing, multilingual generation, etc. See RFC § Open questions.

---

## 10. Recommended future implementation order

1. Complete SKILL-01.1–01.8 Foundation
2. SKILL-02 — MS-SKILL-001 Market Validation runtime (minimal)
3. **SKILL-02.5** — Discovery read model queries + gap report (no generator)
4. SKILL-03 — Connector runtime hardening
5. **SKILL-04** — Tenant-private path + Draft Generator
6. Owner accepts RFC-SKILL-004 → Draft to Accepted

---

## 11. Runtime unchanged confirmation

| Check | Result |
|-------|--------|
| Discovery runtime implemented | **No** |
| Draft Generator implemented | **No** |
| Skill activated | **No** |
| External Skill installed | **No** |
| MCP installed | **No** |
| CWF.1 unchanged | **Yes** |
| CWF.1a unchanged | **Yes** |

SKILL-R0.3 Work Package B is **documentation-only**.

---

## Related

- [SKILL-01.0 package docs](../skills/ms.skill.market_validation.md)
- [SKILL-R0.2 summary](SKILL-R0.2-rfc-drafting-summary.md)
