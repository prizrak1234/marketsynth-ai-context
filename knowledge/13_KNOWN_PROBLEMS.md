# Known Problems

> **Living document.** Add issues as discovered; mark resolved with date in [14_CHANGELOG.md](14_CHANGELOG.md).  
> **Last updated:** 2026-07-30 (MARKET-SYNTH-COMMERCIAL-RESET-01)

---

## P0 — Commercial blockers

| ID | Problem | Impact | Track |
|----|---------|--------|-------|
| P0-01 | BIV report integrity — unsubstantiated verdict, boilerplate as confirmed findings | Owner rejection 2026-07-24; blocks re-acceptance | PRODUCT-01.3 |
| P0-02 | Generic prefilled idea analyzed without user confirmation | Commercial dishonesty | PRODUCT-01.3 |
| P0-03 | Analysis stages green without readable section outputs | Fake progress UX | PRODUCT-01.3 |
| P0-04 | Evidence-gate stop → `output=null`, partial artifacts discarded | Owner re-smoke FAIL; generic failure UI | **RUNTIME-01C** |
| P0-05 | Dual intake paths (7-step vs short BIV) + false home capability cards | User confusion; wrong path fixes | **RUNTIME-01E** |

**Acceptance note:** CMVP.1.1 acceptance is **historical**; current commercial acceptance **invalidated** until RUNTIME-01G owner smoke PASS.

---

## P1 — Product gaps (CWF)

| ID | Problem | Source |
|----|---------|--------|
| P1-01 | Launch Pack missing skill runtimes: audience, positioning, launch plan, posts, visuals | CWF-SKILL-INTEGRATION-GAPS |
| P1-02 | Intent cards B–F route to generic assistant, bypass governed skills | MARKET-SYNTH-COMMERCIAL-RESET-01 |
| P1-03 | Review queue empty shell at `/workspace/review` | Audit — hide in 01E |
| P1-04 | Channels empty shell at `/workspace/channels` | Audit — hide in 01E |
| P1-05 | Content Factory off main path (owner preview only) | Audit |
| P1-06 | Publication execute blocked in UI | CWF audit |
| P1-07 | Offer Builder runtime exists but **not frozen** | AGENTS.md |
| P1-08 | Projects list unproven: click → canonical workspace → hydrate → refresh | Audit — **PARTIAL/REWORK** |
| P1-09 | Legacy short BIV + sync `/run` classified PARTIAL/LEGACY (not BROWSER_READY) | Audit |

---

## Technical debt

| ID | Problem | Risk |
|----|---------|------|
| TD-01 | BIV implemented separately from `ms.skill.market_validation` | Dual maintenance |
| TD-02 | Legacy Alpha routes parallel to CWF home | User confusion |
| TD-03 | Recovery preview R3 redirect orphans Content Factory panel | Dead path |
| TD-04 | market_validation v0.1.0 vs v0.2.0 version ambiguity | Wrong package loaded |
| TD-05 | KB-WPL discovery routes not reflected in product UI | Capability drift |
| TD-06 | 651+ docs in `docs/` without unified SoT index (partially addressed by this SoT) | Context loss |

---

## Frozen track constraints (not bugs — honor gates)

| Constraint | Notes |
|------------|-------|
| VIDEO frozen | P0 bugfixes on i2v only |
| No VS.2B / text-to-video / long-form | Until Controlled Pilot |
| DIS implementation forbidden | Until CGP.10C |
| KB-WPL-02 blocked | Until Product P0 accepted |
| No Instagram/LinkedIn publish | By design AI.75 |
| No background workers | By design |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Chat reset loses dev context | This SoT + session log |
| Skill/CWF drift continues | PRODUCT-00.5 audit after 01.3 |
| Higgsfield connector without owner gates | CONN-HF-01.1L |
| Identity shipped before quality gate | H2.8E owner diagnostic block |

---

## Open questions

| Question | Owner decision needed |
|----------|-------------------------|
| Public pricing tiers | Not documented in repo |
| When to promote KB-WPL-02 | After PRODUCT-01.3 acceptance |
| LLM fallback default for production | Currently off |
| Content Factory on main path timing | After PRODUCT-MEDIA-01? |

---

## Resolved (history)

| ID | Problem | Resolved |
|----|---------|----------|
| PS-01 | Backend availability tests failed (migration head drift) | 2026-07-29 PRESMOKE-FIX-01 |
| PS-02 | Multi-project auto-verdict on cold load | 2026-07-29 PRESMOKE-FIX-01 |
| PS-03 | Incomplete recovery continue dead-end | 2026-07-29 PRESMOKE-FIX-01 |

Add resolved items here with date — never delete the original from decisions/sessions history.
