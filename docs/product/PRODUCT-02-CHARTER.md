# PRODUCT-02-CHARTER

> **Program:** PRODUCT-02 Commercial Product Blueprint  
> **Type:** Architecture / product design — **docs only**  
> **Patch:** PRODUCT-02-BLUEPRINT-PATCH-01 (2026-08-02)  
> **Status:** OWNER-APPROVED decisions applied · pack **ready_for_owner_freeze** · `owner_freeze` **NOT SET**

---

## 1. Purpose

Design the second half of Marketsynth as one commercial system after research/verdict: Strategy → Launch → Content/Visuals → Publication → Outcome Capture, plus how Analytics, Optimization, and support capabilities attach.

PRODUCT-02 answers: *after «Продолжить», how does one Project evolve?*  
It does **not** implement that evolution. Freeze accepts architecture; runtime requires a separate owner priority decision.

---

## 2. Commercial thesis (OWNER-APPROVED)

The user does **not** buy “research as a product.”  
The user buys **development of one business idea**.

| Layer | Role |
|-------|------|
| **Workspace** | Account shell: Home, Projects index, Settings; future Portfolio Analytics (reserved) |
| **Project** | Commercial unit — **Project Command Center** |
| **Capability** | Project stage, project service, workspace service, settings/admin, reserved, or internal — **never** a standalone app |

---

## 3. Canonical topology (OWNER-APPROVED)

```
Workspace
│
├── Home
├── Projects
├── Settings / Admin
│     ├── General, Security/Integrations
│     ├── Billing, Team
│     └── Reserved support (placement TBD until journey): HR, Legal, Finance, Programmer, CRM
│
└── Project  ← Command Center
      │
      ├── Intake
      ├── Research
      ├── Strategy
      ├── Launch
      │     ├── Offer / Channels / Budget / Checklist
      │     ├── Content   ⎤ parallel capability runs
      │     ├── Visuals   ⎦
      │     ├── Approval
      │     └── Publication (multi-instance)
      ├── Project Analytics (operational)
      └── Optimization (post-MVP loop)
```

---

## 4. Decision status vocabulary (OD-10 · OWNER-APPROVED)

| Status | Meaning |
|--------|---------|
| **OWNER-PROPOSED** | Draft / kickoff intent — not binding |
| **OWNER-APPROVED** | Owner accepted for patch / freeze candidate |
| **OWNER-FROZEN** | Owner signed freeze checklist — change requires new program |
| **SUPERSEDED** | Replaced by a later decision |

Documents must **not** self-declare **LOCKED** or **OWNER-FROZEN** without owner action.

---

## 5. Owner-approved decisions (OD-01…OD-10)

| ID | Decision | Status |
|----|----------|--------|
| OD-01 | Split ProjectLifecycleState + CapabilityRunState + ArtifactVersionState + ApprovalRecord | OWNER-APPROVED |
| OD-02 | Analytics dual-layer: Project operational + Workspace Portfolio reserved | OWNER-APPROVED |
| OD-03 | Capability taxonomy A–F; HR default not a project stage | OWNER-APPROVED |
| OD-04 | Content & Visuals parallel under Launch | OWNER-APPROVED |
| OD-05 | MVP spine cut (through one Publication + basic Outcome Capture) | OWNER-APPROVED |
| OD-06 | Optimization = post-MVP cyclic capability; versioned candidates | OWNER-APPROVED |
| OD-07 | Publication multi-instance (assets/packages/jobs/channels) | OWNER-APPROVED |
| OD-08 | Partial Research → Strategy blocked unless explicit override | OWNER-APPROVED |
| OD-09 | CRM reserved; classification later | OWNER-APPROVED |
| OD-10 | Decision vocabulary OWNER-PROPOSED / APPROVED / FROZEN / SUPERSEDED | OWNER-APPROVED |

---

## 6. Goals

1. Small stable **Project** lifecycle; runs and approvals elsewhere.  
2. Commercial spine as **orchestration graph** (not a single conveyor enum).  
3. Expanded Capability Catalog with A–F + MVP/post-MVP/reserved.  
4. Versioned **artifact lineage graph** + **ApprovalRecord** semantics.  
5. Topology ready for freeze; IA/Registry patches only **after** freeze.  
6. Explicit MVP boundary ≠ full catalog.

---

## 7. Out of scope

| Forbidden | Why |
|-----------|-----|
| Code, UI, backend, migrations | Docs-only |
| Real research / Evidence Hardening | Until 2026-08-18 |
| Strategy/Launch/… **runtime** | Separate owner priority after freeze |
| Slice G implementation | Blocked until freeze |
| Treating Registry as authorization | UX exposure only |
| Pseudo-DB schemas / table designs | Semantic contracts only |
| Declaring support services as MVP because they appear in the catalog | Catalog ≠ first payment |

---

## 8. Forbidden design pattern

Core capabilities (Strategy, Launch, Analytics, …) and reserved support domains (CRM, HR, Legal, Finance, Programmer) are **not** independent applications with their own primary navigation and product UX.

Support capabilities are **not** automatically Project stages.

---

## 9. Registry relationship

| Layer | Owns |
|-------|------|
| **Capability Registry** | Existence, availability, public/internal/reserved, nav/CTA exposure |
| **PRODUCT-02** | Lifecycle layers, classification, artifacts, approvals, topology, MVP cut |
| **Backend authz** | Tenant/project ownership and approver roles — **independent of Registry** |

---

## 10. Definition of Done (PATCH-01)

1. OD-01…OD-10 applied across the seven SoTs.  
2. P0 audit findings closed.  
3. Freeze-blocking P1 closed.  
4. `owner_freeze` remains **NOT SET**.  
5. Pack status: **ready_for_owner_freeze**.

---

## 11. After owner freeze (not automatic)

```
Owner freeze (OWNER-FROZEN)
  → IA + Journey + Registry alignment docs/tasks
  → 2026-08-18 Research Hardening (unless owner reprioritizes)
  → Strategy Runtime TZ (separate decision)
  → …
```

Freeze ≠ start Strategy Runtime.
