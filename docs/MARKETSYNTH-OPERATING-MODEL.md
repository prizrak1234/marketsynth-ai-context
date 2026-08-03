# Marketsynth Operating Model

**Status:** `owner_canonical` · **Level:** CEO / platform architecture  
**Term:** **AI Business Operating System (AI Business OS)** — preferred internal and external framing  
**Implementation:** reference model — new modules **must** map here before build  
**Companion docs (trilogy):**

| # | Document | Question |
|---|----------|----------|
| 1 | [PROJECT_VISION.md](./PROJECT_VISION.md) | **Why** does Marketsynth exist? |
| 2 | [product/MARKETSYNTH-PLATFORM-MAP.md](./product/MARKETSYNTH-PLATFORM-MAP.md) | **What** domains does it consist of? |
| 3 | **This document** | **How** do all parts work together? |

Legacy package label: **BotFazer** (code internals unchanged until migration phase).

---

## One-sentence model

> Marketsynth is an **AI Business OS** where every capability runs the same loop — **observe → decide with evidence → approve → execute → measure → learn** — inside a shared **Workspace**, governed by **Human Approval**, recorded in **Knowledge**, and executed through a unified **Execution Layer**.

Marketing ≈ **20–25%** of the platform surface. The rest is research, decisions, production, development, automation, execution control, and (future) business intelligence.

---

## 1. Customer lifecycle (canonical platform journey)

This is **how the user passes through the platform** — not a feature list.

```
Идея
  ↓
Регистрация / онбординг
  ↓
Workspace (проект создан)
  ↓
Исследование (Research / BIV)
  ↓
Вердикт (коммерческое решение)
  ↓
Маркетинговая стратегия
  ↓
Pre-Launch Readiness
  ↓
Campaign Architect (режим + цель + формат)
  ↓
Content Factory
  ↓
Website Builder
  ↓
Creative Studio (Design)
  ↓
Video Factory
  ↓
Copywriting (сквозной — также внутри фабрик)
  ↓
AI Developers (Programmer Domain)
  ↓
Automation (Make / n8n / API / webhooks)
  ↓
Execution (Direct, Telegram, marketplaces, …)
  ↓
Analytics / Measurement
  ↓
Optimization
  ↓
Business Intelligence (долгосрочно)
```

**Rules:**

- Stages are **not** always linear — user may enter mid-chain (e.g. existing business → Readiness → Direct).
- Skipped stages must show **honest gap** («стратегия не подтверждена», «аналитика не настроена»).
- **No stage auto-runs** the next without explicit user intent or approved recipe.
- Commercial wedge (CWF.1) today: **Idea → Research → Verdict → Launch Pack → Telegram** — a **prefix** of this journey, not the whole OS.

---

## 2. Module roles (who does what)

| Module / domain | Role (one verb) | Thinks / plans / builds / runs |
|-----------------|-----------------|--------------------------------|
| **Research** | **Understands** | Thinks — evidence-backed picture of market, demand, risk |
| **Strategy** | **Plans** | Plans — positioning, offer, CJM, launch logic |
| **Pre-Launch Readiness** | **Gates** | Protects — blocks spend on broken infrastructure |
| **Campaign Architect** | **Designs** | Plans — mode, objective, format, budget fit |
| **Website Builder** | **Builds** | Builds — landing, store, corp site, publish |
| **Copywriting** | **Writes** | Produces — texts across all surfaces |
| **Design / Creative Studio** | **Visualizes** | Produces — brand, banners, decks, assets |
| **Video Factory** | **Produces** | Produces — motion, scripts, avatars, subs |
| **Content Factory** | **Publishes** | Produces + distributes — channel posts, plans |
| **AI Developers** | **Implements** | Builds — bots, agents, integrations, code |
| **Automation** | **Connects** | Integrates — CRM, webhooks, workflows |
| **Execution (Direct, Ads, …)** | **Launches** | Runs — paid/owned media with audit trail |
| **Analytics** | **Measures** | Observes — goals, attribution, honest limits |
| **Optimization** | **Improves** | Learns — recommendations, A/B, budget shift |
| **Business Intelligence** | **Controls** | Governs — why sales/CAC/channels changed |
| **Knowledge Base** | **Remembers** | Cross-cutting — reuse, lineage, citations |
| **Workspace** | **Hosts** | Cross-cutting — projects, history, artifacts |
| **Human Approval** | **Authorizes** | Cross-cutting — gate before irreversible action |
| **AI Team (specialists)** | **Expertise** | Skills inside domains — not separate islands |

**Anti-pattern:** a module that only «generates text» without Input → Evidence → Decision → Approval → Outcome is **not** a Marketsynth subsystem — it is a feature fragment.

---

## 3. Runtime loop (the OS heartbeat)

Every substantial capability participates in the **same runtime loop**. This is not «research → report» and stop.

```
        ┌────────── Observe ──────────┐
        │  intake, metrics, gaps,     │
        │  supervisor signals         │
        └─────────────┬───────────────┘
                      ↓
                 Research
        (gather, fetch, extract — evidence)
                      ↓
                  Reason
        (findings, verdict, plan, recommendation)
                      ↓
                  Approve
        (human gate — mandatory for critical paths)
                      ↓
                  Execute
        (tools, providers, publish, spend)
                      ↓
                  Measure
        (analytics, outcomes, ledger)
                      ↓
                   Learn
        (what worked, rejection reasons, deltas)
                      ↓
                  Improve
        (next action, recheck, optimization)
                      ↓
        └────────── Observe ──────────┘
```

**Mapping to product today:**

| Loop stage | Primary home today | Persistence |
|------------|-------------------|-------------|
| Observe | Workspace, Campaign Control Center, supervisor | Project / campaign state |
| Research | BIV, Research Engine | Run, fetch ledger, evidence items |
| Reason | Verdict, strategy, Campaign Architect docs | Reports, plans |
| Approve | Human Approval, explicit confirm flags | Audit id, consent |
| Execute | Execution Layer, publishing, Direct (future) | Execution runs, ledger |
| Measure | Analytics adapters, pipeline metrics | Observability JSON |
| Learn | Knowledge candidates, gap presentation | KG draft candidates |
| Improve | Action Center, remediation, recheck | Fix plan, new run version |

**Rule:** A module that stops at **Reason** without a path to **Approve → Execute → Measure** is **read-only by design** (e.g. supervisor) or **incomplete**.

---

## 4. Shared platform services (describe once)

These are **not** product features — they are **OS services** every module uses.

### Knowledge Base

**Used by:** Research · Strategy · Content · AI Developers · BI · all specialists  

**Must:** accumulate outcomes; cite sources; support reuse; admission = draft candidate → governed snapshot (KG architecture).

**Contract:** Answer + Evidence + Source + Confidence.

### Workspace

**Used by:** all modules  

**Hosts:** projects · user requests · runs · versions · reports · publications · files · hydration history.

**Rule:** User-facing business state lives here — not inside chat transcripts alone.

### Human Approval

**Used by:** all modules with irreversible or paid effects  

**Pattern:** AI proposal → explicit human accept → execution  

**Examples:** publish, paid smoke, campaign launch, neural ads, Controlled Performance mode.

### Execution Layer

**Used by:** Direct · Telegram · marketplaces · automation triggers · future channels  

**Must:** audit trail · idempotency · provider outcome · no dry-run as real publish.

### Identity (Digital Identity / DIS — future slices)

**Used by:** Design · Video · Content · brand-consistent production  

**Gate:** architecture accepted; implementation after CGP.10C + narrow vertical slices.

### Billing (future)

**Used by:** all paid execution paths  

**Must:** meter at execution boundary · align with commercial SKU.

### Observability

**Used by:** all modules  

**Must:** stage metrics · failure codes · operator diagnostics · honest customer limits.

**Rule:** New module **declares** which shared services it consumes — no duplicate ad-hoc memory/approval stacks.

---

## 5. Universal module invariant

Every governed module **must** implement this chain (Subsystem Standard alignment):

```
Input
  ↓
Evidence          (or explicit «insufficient evidence» — never fake)
  ↓
Decision          (recommendation, plan, artifact — traceable to evidence)
  ↓
Approval          (human where critical; logged)
  ↓
Execution         (optional — read-only modules stop at Decision)
  ↓
Outcome           (persisted, versioned, customer-visible where applicable)
  ↓
Knowledge Candidate   (successful patterns admissible to KB — not auto-published)
```

**Rejections at any stage** require a **coded reason** (same philosophy as Evidence Funnel audit).

**Examples:**

| Module | Execution? |
|--------|------------|
| Research / BIV | Outcome = verdict + report; execution = external fetch only |
| Pre-Launch Readiness | Outcome = gate status; no media execution |
| Campaign Architect | Outcome = architecture report; execution = downstream Direct |
| Content Factory | Full chain through publish execution |
| Supervisor | Stops at Decision (findings) — never Execute |

---

## 6. Platform readiness levels (internal maturity gates)

Progressive **readiness** — what the platform certifies before unlocking downstream modules:

```
Research Ready
  ↓  evidence-backed verdict or honest HOLD; citation contract
Strategy Ready
  ↓  positioning, offer, plan artifacts linked to research
Launch Ready
  ↓  Pre-Launch PASS; Campaign Architect complete; assets minimum
Growth Ready
  ↓  execution live; analytics measuring; optimization loop closed once
Business Ready
  ↓  multi-channel; automation; CRM signals; BI prerequisites met
```

| Level | Unlocks (examples) | Blocks |
|-------|-------------------|--------|
| Research Ready | Strategy, honest Launch Pack | Paid ads at scale |
| Strategy Ready | Production factories, site builder | Execution without readiness |
| Launch Ready | Execution Layer, real publish | Expert/EPC without data |
| Growth Ready | Optimization, budget increase | Autonomous spend |
| Business Ready | BI, autonomous recommendations | — |

**Today:** Research Ready is **hard-pblocked** until Evidence Funnel PASS (HARDENING-02).

---

## 7. Business maturity map (customer journey vs modules)

Platform maturity of the **customer's business** — which modules **serve** each stage:

| Business stage | Customer state | Primary modules |
|----------------|----------------|-----------------|
| **Idea** | Hypothesis only | Research, Workspace |
| **Validated** | Evidence + verdict | Research, Strategy, Knowledge |
| **First Customer** | Offer + landing + first traffic | Website, Copy, Content, Direct (wizard), Readiness |
| **Repeatable Sales** | Known CAC, goals, CRM | Execution, Analytics, Automation, Copy, Design |
| **Growth** | Multi-segment, budget scale | Campaign Architect (expert), Video, Content scale, Optimization |
| **Scaling** | Team, ops, integrations | AI Developers, Automation, AI Team expansion |
| **Autonomous Business** | Closed measurement loop | BI, Optimization, Knowledge reuse at org level |

This is **not a roadmap** — it is **maturity alignment**. Engineering priority still follows commercial P0 gates (see Platform Map queue).

---

## 8. How modules plug in (anti-island rule)

Before any new module, RFC, or specialist is accepted, it must answer:

1. **Which lifecycle stage(s)** does it serve?  
2. **Which runtime loop stage(s)** — Observe through Improve?  
3. **Which shared services** does it require?  
4. **Where does Human Approval** sit?  
5. **What Outcome** is persisted in Workspace?  
6. **What Knowledge Candidate** does it emit?  
7. **Which readiness level** does it require and which does it unlock?

If any answer is «standalone chat skill» → **reject or redesign**.

**Subsystem Standard:** substantial capabilities also need lifecycle, operator, manifest, honest capability ([marketsynth_subsystem_standard.md](./architecture/marketsynth_subsystem_standard.md)).

---

## 9. Architecture vs product (current state)

| Layer | State |
|-------|--------|
| Operating Model (this doc) | **Canonical** — how things should connect |
| Platform Map | **Canonical inventory** — what exists / planned |
| Module RFCs (Campaign Mode, Ad Format, Pre-Launch, Evidence Funnel, …) | **Ahead of product** in places — correct if they plug into §3–§8 |
| Runnable product (CWF.1, BIV, Workspace, Telegram) | **Behind** full journey — prefix of lifecycle |

**Danger (now):** each new module lives alone → expensive integration later.  
**Antidote:** no new selector/specialist/campaign doc without §8 checklist pass.

---

## 10. Freeze until Operating Model is respected

**Do not open** (even as architecture) until owner accepts this model:

- New specialist role / department expansion RFC  
- New selector / architect slice beyond already-accepted Campaign Mode + Ad Format  
- New campaign submodule docs  

**Continue** (active P0):

- [EVIDENCE-FUNNEL-ARCHITECTURE.md](./product/EVIDENCE-FUNNEL-ARCHITECTURE.md) — HARDENING-02; implements Research → Reason with measured funnel; fits Runtime Loop.

---

## 11. Terminology (team standard)

| Use | Avoid as primary framing |
|-----|--------------------------|
| **AI Business OS** / **AI Business Operating System** | «AI marketing agency» as whole product |
| **Module** / **domain** | «Agent» as product surface for users |
| **Runtime loop** | «Pipeline finished» when only report exists |
| **Readiness level** | «Feature complete» without customer outcome |
| **Execution Layer** | «Integration done» without audit trail |

Marketing remains a **strong wedge** and **first paid SKU** — not the **definition** of the company.

---

## 12. Cross-references

- [AGENT_OS_ARCHITECTURE.md](./AGENT_OS_ARCHITECTURE.md) — Skills/Tools/Supervisor inside Agent layer (nested in this OS)  
- [architecture/marketsynth_subsystem_standard.md](./architecture/marketsynth_subsystem_standard.md) — governed subsystem lifecycle  
- [HOME_PRODUCT_RULE.md](./HOME_PRODUCT_RULE.md) — Home = business decisions, not control panel  
- [CURSOR_OPERATING_RULES.md](./CURSOR_OPERATING_RULES.md) — gates, frozen layers  
- [product/EVIDENCE-FUNNEL-ARCHITECTURE.md](./product/EVIDENCE-FUNNEL-ARCHITECTURE.md) — active P0 inside Research stage  

---

## Document maintenance

When adding a domain to Platform Map → update **§2 role**, **§1 lifecycle** if user-visible, and **§7 maturity row**.  
When adding a shared service → update **§4** only once.  
When shipping a commercial slice → verify **§5 invariant** end-to-end in browser.

**This document wins** over orphan module docs when they conflict on «how things connect.»
