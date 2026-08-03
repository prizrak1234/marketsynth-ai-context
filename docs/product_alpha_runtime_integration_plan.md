# Product Alpha Runtime Integration Plan

**Companion to:** [`product_alpha_ai591_reconciliation_audit.md`](./product_alpha_ai591_reconciliation_audit.md)  
**SoT detail:** [`product_alpha_source_of_truth_matrix.md`](./product_alpha_source_of_truth_matrix.md)  
**Constraint:** continue existing BotFazer/Marketsynth runtime — do not ship a parallel Runtime.

---

## Goals

1. Preserve Product Alpha A1–A6 as the **commercial UX journey**.
2. Bind that UX to the **existing** Campaign Control Center + Projects + Marketing pipeline.
3. Fill only real gaps (Investigation, Verdict, Strategy, planning handoff) as additive contracts.
4. Defer A7 and AI.592-class execution_mode work until the Workspace↔Runtime map is live.

---

## Non-goals (now)

- Implementing A7 Execution Package as product path
- Starting AI.592 / execution_mode productization
- Creating AgencyRole AgentTypes
- Replacing Campaign Control Center APIs
- Fake provider / real spend execution from Alpha screens

---

## Architecture principle

```
Marketsynth Workspace (UI)
        │  adapters / read models
        ▼
Existing Runtime SoT
  • Project / Campaign
  • Campaign Control Center (health, next_action, timeline)
  • Supervisor
  • MarketingPlan + execution runs + specialists
  • Brief / Action / Approve / Publish spine
        │
        ▼ (later)
Additive domain
  • Investigation + Evidence
  • BusinessVerdict (VerdictKind)
  • MarketingStrategy (or artifact package)
  • ImplementationPlan ↔ MarketingPlan handoff
        │
        ▼ (after integration)
Architecture V2.2 Verified Execution / A7-shaped package
```

---

## Revised sequence (preferred)

### Phase F0 — Freeze Product Alpha A1–A6

- Mark A1–A6 UX as **prototype freeze**.
- Stop expanding mock localStorage domains.
- Treat any local A7 code/docs as **parked**, not next work.

**Exit:** written freeze note in AGENTS/DEVELOPMENT (when implementation phase allows doc update).

### Phase I1 — Control Center reconciliation (not missing AI.591)

- Document field map: Alpha Agency Runtime Monitor ← `CampaignControlCenter` + supervisor + specialist runs.
- Decide campaign deep-link UX inside `/workspace`.
- **Do not** invent `workforce`/`current_stage` backend fields until overlay design is explicit and additive.

**Exit:** Monitor field mapping table approved.

### Phase I2 — Read-only Runtime Monitor wiring

- Replace mock specialists/next-step/timeline with **read-only** fetches.
- Preserve Alpha visual hierarchy; strip fake “live runtime” claims.

**Exit:** Monitor shows real campaign-scoped data for at least one seeded demo project.

### Phase I3 — Active Projects from API

- Replace `proj_alpha` mocks with `GET /projects` (+ campaign summaries).
- Derived Alpha `ProjectStatus` labels only — **no** new Project.status enum without contract.

**Exit:** empty/full workspace states work against API.

### Phase I4 — Intake → Project + Brief

- Map `ProjectIntakeDraft` → create/update Project + Campaign Brief fields.
- Keep wizard UX; drop silent dual storage when API write succeeds.

**Exit:** “Начать исследование” creates real project (+ brief) and navigates with real id.

### Phase I5 — Investigation read models

- Prefer additive Investigation/Evidence contracts (`contracts.py` first).
- Interim acceptable: project skill-run + tool-result projection labeled as incomplete investigation.

**Exit:** Investigation screen reads server data; localStorage degraded to cache/offline draft only.

### Phase I6 — Verdict / decision semantics

- Persist BusinessVerdict using existing `VerdictKind`.
- Separate Verdict from resource Approvals and from CC `next_action`.
- Keep Alpha routing rules as UI policy over server verdict type.

**Exit:** GO/CONDITIONAL/NO_GO/INSUFFICIENT_DATA round-trip via API.

### Phase I7 — Strategy integration

- Add Strategy entity **or** versioned specialist/skill artifact package with strategy schema.
- Map Alpha conditions/risks to supervisor + strategy fields without duplicating registers blindly.

**Exit:** Strategy workspace loads server version; local approve remains gated until ApprovalRequest exists.

### Phase I8 — Implementation plan integration

- Define handoff: Alpha ImplementationPlan (planning) → create/update `MarketingPlan` (execution spine) via **explicit** endpoint.
- Forbid silent competing plan engines.

**Exit:** “Prepare execution” creates marketing plan tasks from mapped workstreams/tasks.

### Phase I9 — Approvals & readiness alignment

- Map Alpha gates to existing `/approve` where possible.
- Introduce `ApprovalRequest` only if resource approves are insufficient (follow V2.1 notes).
- Readiness becomes server-derived where gates exist.

**Exit:** local-only approve removed from critical paths.

### Phase V — A7 / Architecture V2.2 Verified Execution

- Execution Package as **preview over real readiness + approvals**.
- Dry-run remains non-mutating until V2.2 provider verification.

**Exit:** A7 productized against live readiness — not mock-only.

### Phase E — Execution mode / AI.592-class work

- Only after Workspace shows real Runtime state and handoff rules are clear.
- Decide how `execution_mode` (today `PLANNING`-only) appears in Alpha Workspace without breaking gates.

**Exit:** mode is a backend field projected in UI — not a frontend enum driving execution.

---

## Dependency corrections vs naive sequence

| Naive step | Correction |
|---|---|
| “Reconcile with AI.591 overlay” | Reconcile with **Campaign Control Center AI.156–165**; AI.591 code absent |
| Wire investigation before projects | Projects/list first (I3) so investigation has real ids |
| Persist strategy before verdict | Verdict first (I6) — Alpha routing depends on it |
| Build A7 next | After I8–I9 |
| Continue AI.592 now | **Wait** until E |

---

## Suggested phase labels (avoid colliding with frozen AI.* conveyor)

| Label | Meaning |
|---|---|
| **Alpha F0** | UX freeze A1–A6 |
| **Alpha I1–I9** | Integration slices above |
| **Alpha V / Arch V2.2** | Verified execution package |
| **Alpha E** | Execution mode UI binding (post-I) |

Keep historical AI.27–AI.265 numbering for backend conveyor docs unchanged.

---

## Risk register (integration)

| Risk | Mitigation |
|---|---|
| Dual Control Centers | One API SoT; one commercial home UX |
| AgencyRole → AgentType creep | Alias table only |
| Two plan engines | Explicit handoff API only |
| Alpha “execution” wording vs PLANNING mode | Copy + readiness labels; no fake mode |
| Shipping A7 mock as product | Freeze A7 until V |

---

## Immediate next action after architecture review

1. Approve Control Center decision **A (refined)**.  
2. Start **I1** mapping only (docs + thin read adapter spike if approved).  
3. Keep A7 and AI.592 parked.
