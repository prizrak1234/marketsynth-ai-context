# PRODUCT-00 — Commercial Workflow Reconciliation Audit

| Field | Value |
|-------|-------|
| **Phase** | PRODUCT-00 |
| **Date** | 2026-07-24 |
| **Mode** | Documentation and repository audit only |
| **Verdict** | **READY FOR PRODUCT IMPLEMENTATION** |

---

## Executive summary

KB-WPL-01 closed a strong **knowledge foundation** (15 skill packages on disk, capability model, discovery). The **commercial product surface** is much thinner: only **Business Idea Validation (BIV)** has a governed runtime + customer UI. All SKILL-02 marketing packages—including **`ms.skill.offer_builder`**—exist as **valid candidate contracts** but have **zero `app/` runtime integration** and **no governed UI path**.

The apparent contradiction (SKILL-02.8 planned vs “already in 15 Skills”) is resolved:

| Layer | offer_builder state |
|-------|---------------------|
| Package on disk | ✅ **Exists** — `packages/skills/ms.skill.offer_builder/` v0.1.0 |
| Contract / schemas / tests | ✅ **Complete** — `tests/test_skill_02_8_offer_builder.py` |
| Frozen candidate | ❌ **Not frozen** — `status: candidate`, `executable: false` |
| Runtime loader | ❌ **Missing** — no references in `app/` |
| UI / CWF delivery | ❌ **Missing** — Launch Pack shows offer *labels* only |

**Recommended next slice:** **PRODUCT-01 — Offer Builder completion and CWF integration** (not Content Golden Path first).

---

## Repository reconciliation

### What “15 Skills” means in KB-WPL-01

`packages/skills/` contains **15 packages** total:

- **11 commercial marketing** (SKILL-02 / ARCHIVE-MKT)
- **3 n8n engineering** (KB-WPL-01.4)
- **1 knowledge linking** (KB-WPL-01.5)

Only **presentation_architecture** among KB-WPL skills is `frozen_candidate`. All 11 commercial packages remain **`candidate` / non-executable**.

### Runtime vs package

| Executable runtime | Module | Related skill package |
|--------------------|--------|------------------------|
| ✅ BIV only | `app/business_idea_validation/` | Inspired by market validation methodology; **not** `ms.skill.market_validation` loader |
| ✅ Launch Pack decision | `app/commercial_workflow/`, `app/services/launch_pack_service.py` | CWF.1a — request/decision only |
| ✅ Content Factory (backend) | `app/services/content_factory_generation_service.py` | No dedicated skill package |
| ✅ Telegram publish (backend) | `app/publishing/providers/telegram_provider.py` | Blocked in customer UI |
| ❌ All `ms.skill.*` marketing packages | — | Contract-only |

---

## CWF state vs documentation

### Documented

- **CWF.1a** — `docs/product/CWF.1a-intent-entry-ux.md` (implemented frontend routing)
- **CWF.1 canonical chain** — referenced in code comments and Launch Pack i18n keys; **no standalone CWF.1 RFC on disk**

### Documented CWF.1 Launch Pack scope (from `decision_branch.py`)

Included keys: audience, positioning, **offer**, launch plan, **3 Telegram posts**, visuals, publication prep.

### Actually implemented

```
Idea → BIV (research/verdict) → Decision branch → Launch Pack REQUEST → (stop)
```

No offer artifact, no launch plan, no posts, no visuals generation in customer UI.

---

## Commercial readiness summary

| Status bucket | Count | Examples |
|---------------|-------|----------|
| production_user_ready | 1 journey | A — Проверить идею (BIV) |
| integrated_but_unpolished | 1 | K — Launch Pack decision (request only) |
| contract_only | 11 | All SKILL-02 marketing packages incl. offer_builder |
| documentation_only | 0 | — |
| deferred (capability, no package) | 3+ | content_strategy, copywriting, launch_strategy |
| missing | 4+ | visual_brief, dedicated Telegram/YouTube skills |
| conflicting | 2 | Content intents → assistant; Launch Pack promises vs delivery |

---

## P0 commercial blockers

1. **Launch Pack stops at request** — no Offer / Launch Plan / 3 posts delivered after CTA.
2. **`offer_builder` package exists but no runtime** — blocks Offer journey (F) and weakens Launch Pack (K).
3. **Content intents (G/H/I) route to generic assistant** — not Content Factory or copywriting skill.
4. **Publication (L) UI blocked** — backend `execute` exists; frontend dry-run only; review/channels empty.

---

## Recommended next phase

**PRODUCT-01 — Offer Builder completion and CWF integration**

Scope sketch (not implemented in PRODUCT-00):

1. Dry-run / operator execution path for `ms.skill.offer_builder` using existing schemas
2. Wire Launch Pack delivery to produce reviewable Offer artifact post-verdict
3. Intent routing: post-verdict “создать оффер” → governed workflow, not generic assistant
4. UI acceptance gate before Content Golden Path

**Do not start** KB-WPL-02 Knowledge Core Persistence until P0 journey slice is owner-accepted.

---

## Verdict rules applied

| Rule | Result |
|------|--------|
| Repository state reconciled | ✅ |
| Next P0 slice unambiguous | ✅ PRODUCT-01 Offer Builder + CWF |
| Skill/package existence consistent | ✅ (package ≠ runtime clarified) |
| Frozen hashes drifted | ❌ None detected in audit |
| CWF path determinable | ✅ with documented drift |

**Verdict: READY FOR PRODUCT IMPLEMENTATION**

---

## Related documents

- [COMMERCIAL-SKILL-INVENTORY.md](COMMERCIAL-SKILL-INVENTORY.md)
- [USER-JOURNEY-READINESS-MATRIX.md](USER-JOURNEY-READINESS-MATRIX.md)
- [CWF-SKILL-INTEGRATION-GAPS.md](CWF-SKILL-INTEGRATION-GAPS.md)
- [PRODUCT-TRACK-PRIORITY-PLAN.md](PRODUCT-TRACK-PRIORITY-PLAN.md)

---

## Audit constraints (confirmed)

- No new Skill created
- No runtime changed
- No UI changed
- No frozen package modified
- No Connector activated
- No deployment performed
