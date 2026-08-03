# Roadmap

> **Approved work only.** Ideas belong in [07_BACKLOG.md](07_BACKLOG.md).  
> **Last updated:** 2026-08-02 (**PRODUCT-CD-RUNTIME-01** Text Golden Path)

---

## Active product architecture (docs)

| ID | Status | Notes |
|----|--------|-------|
| **Commercial Decision Engine** | **FROZEN** | Research validation blocked until 2026-08-18; no user value from continuing now |
| **PROGRAM-CONTENT-01** | **OPEN** | AI Creative Platform |
| **PRODUCT-02…05 packs** | **OWNER-FROZEN** | Remain binding; PRODUCT-05 = Text seed |
| **PRODUCT-CD-RUNTIME-01** | **implemented_verified** | Text telegram_post Golden Path — await owner acceptance |
| **PRODUCT-CD-RUNTIME-02** | **NOT STARTED** | Image Runtime — after Text owner PASS only |
| **PROGRAM-CONTENT-01-VISUAL-ARCHITECTURE** | **NOT STARTED** | Architecture track; Runtime Image is separate |
| **PROGRAM-CONTENT-01-VIDEO-ARCHITECTURE** | **NOT STARTED** | After Visual (or owner order) |
| **Creative Review / Asset Library / Provider Adapter** | **NOT STARTED** | Docs after domain packs |
| **PRODUCT-03-STRATEGY-RUNTIME** | **Paused** | Audit complete; impl not started |
| **Research Evidence Hardening** | **PAUSED** until **2026-08-18** | Decision Engine resume by owner |
| **Publication Architecture** | **NOT STARTED** | Handoff boundary; sequence with Creative |
| **Slice G / Billing / Team / HR / CRM / Legal** | **BLOCKED** | Not current program |

**Active focus:** Skill Runtime + Content Director Text Runtime acceptance → Image Runtime (owner-gated, do not auto-start).  
**Not active:** Strategy/Launch/Research Runtime, Video, Publication execute.

**Rule:** Artifacts > models. No new foundation. Pattern/Fabric semantics only. PRODUCT-05 freeze not casually rewritten.

PRODUCT-02 (frozen): `docs/product/PRODUCT-02-*` · `OWNER-FREEZE.md`  
PRODUCT-03 pack: `docs/product/PRODUCT-03-STRATEGY-*.md`  
PRODUCT-04 EM: `docs/product/PRODUCT-04-EXECUTION-MODEL.md`  
PRODUCT-04 Fabric: `docs/product/PRODUCT-04-EXECUTION-FABRIC.md`  
Fabric audit: `docs/product/PRODUCT-04-EXECUTION-FABRIC-AUDIT.md`  
Launch Domain Model: `docs/product/PRODUCT-04-LAUNCH-DOMAIN-MODEL.md`  
Launch Architecture pack: `docs/product/PRODUCT-04-LAUNCH-ARCHITECTURE.md` (+ Lifecycle, Catalog, Artifact Flow, Journey, MVP Cut, Audit/Freeze)  
Content Architecture pack: `docs/product/PRODUCT-05-CONTENT-ARCHITECTURE.md` (+ Lifecycle, Artifact Flow, Journey, MVP Cut, Audit/Freeze)  
Unqualified **PRODUCT-03** = Strategy Architecture (Visual path = LEGACY / SUPERSEDED_ID)


---

## Completed (selected)

| Phase | Description | Acceptance |
|-------|-------------|------------|
| CMVP.1 / CMVP.1.1 | Business Idea Validator | Accepted (`006b087`) |
| VS.1 | Video smoke foundation | Implemented |
| VS.2A-P-R | Image→video in Commercial Home | Accepted 2026-07-22 (`691dccc`) |
| KB-WPL-01 | Integrated workflow pattern library freeze | Closed 2026-07-24 |
| AI.27–AI.265 | Marketing conveyor + dept v2 + campaigns | Frozen per phase audits |
| AI.60–AI.100 | Publishing, demo, beta | Frozen |
| CWF.1a | Intent entry UX routing | Implemented |
| PRODUCT-02 | Commercial Product Blueprint | **OWNER-FROZEN** 2026-08-02 |
| PRODUCT-03 | Strategy Architecture | **OWNER-FROZEN** 2026-08-02 |
| PRODUCT-04-EXECUTION-MODEL | Commercial Execution Model | **OWNER-FROZEN** 2026-08-02 |
| PRODUCT-04-EXECUTION-FABRIC | Marketsynth Execution Fabric | **OWNER-FROZEN** 2026-08-02 |
| PRODUCT-04-LAUNCH-DOMAIN-MODEL | Launch Domain Model | **OWNER-FROZEN** 2026-08-02 |

Detail: [milestones/](milestones/)

---

## Future (planned, not active)

| Area | Notes |
|------|-------|
| PRODUCT-04-LAUNCH-ARCHITECTURE-01 | Formal kickoff when owner sets next priority; docs-only; must not re-decide EM |
| KB-WPL-02 | **Do not start** until Product Track P0 owner-accepted |
| VS.2B+ video | Blocked until Controlled Pilot |
| DIS implementation | Blocked until CGP.10C + vertical slices |
| Multi-channel publish | Out of CWF.1 scope |
| Billing / CRM / Ads dashboard | Post-pilot (class D) |
| Business Intelligence | Long-term platform map |

---

## Frozen layers (no extension without explicit phase)

- Marketing pipeline AI.27–39
- Video track (P0 bugfixes on i2v only)
- Telegram-only publishing (no Instagram/LinkedIn)
- 14-role marketing department v2 baseline
- Project freeze tag: `project-freeze-2026-07-22`
- PRODUCT-02 / PRODUCT-03 / PRODUCT-04-EXECUTION-MODEL / PRODUCT-04-EXECUTION-FABRIC / PRODUCT-04-LAUNCH-DOMAIN-MODEL owner freezes

---

## Roadmap vs backlog

| Roadmap | Backlog |
|---------|---------|
| Owner-approved phases with acceptance criteria | Ideas, improvements, technical curiosity |
| Has phase docs / RFC acceptance | No automatic promotion |
| Tracked in AGENTS.md active track | Tracked in [07_BACKLOG.md](07_BACKLOG.md) |
