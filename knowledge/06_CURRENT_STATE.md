# Current State

> **This file must always describe reality.** Update after every significant session.  
> **Last updated:** 2026-08-03 (**WORKSPACE-BOOT-RECOVERY-02** · automated_verified · await owner visual)

---

## Active Execution

| Field | Value |
|-------|-------|
| **Active program** | **PROGRAM-CONTENT-01** — AI Creative Platform |
| **Task** | **WORKSPACE-BOOT-RECOVERY-02** Deterministic workspace boot (no hard reload) |
| **Status** | **automated_verified** · owner_visual_ready **YES** |
| **COMMERCIAL-PROJECT-START-01** | **automated_verified** · owner_accepted **NOT SET** |
| **PROJECT-COMMAND-CENTER-CANONICAL-01** | **automated_verified** · owner_accepted **NOT SET** |
| **PROGRAM-CONTENT-01-UX-INTEGRATION-01** | **FAILED_OWNER_VISUAL** |
| **PROGRAM-CONTENT-01-UX-INTEGRATION-01-REGRESSION-FIX** | superseded by CANONICAL-01 |
| **PRODUCT-CD-RUNTIME-02** | **automated_verified** · owner_accepted **NOT SET** |
| **Video Runtime** | **NOT STARTED** |
| **owner_visual_acceptance** | **NOT SET** |
| **owner_accepted** | **NOT SET** |
| **Forbidden** | Video Runtime · autonomous COO · new global sidebar · Asset Library · live paid gen from General |
| **Next** | Owner visual: bare `/workspace` → PCC without Ctrl+F5 / re-login — no OWNER-ACCEPTED until eyes-on |

### Architecture thesis

Marketsynth has two halves: **Decision** (Idea→Research→Strategy→Launch) and **Creation** (materials→review→versions→export→publish). Decision foundations are OWNER-FROZEN but blocked on Research validation until 18 Aug. Active value work = **Creative Platform**. Automated green ≠ owner-visible commercial delivery.

### Owner commercial route (2026-08-03)

```
Commercial Decision Engine  ← FROZEN until 18.08.2026
        ↓
PROGRAM-CONTENT-01 AI Creative Platform  ← ACTIVE
  → Text/Skill/Image GP = automated_verified (owner_accepted NOT SET)
  → CANONICAL-01 PCC · COMMERCIAL-PROJECT-START-01 · WORKSPACE-BOOT-RECOVERY-02
  → Video Foundation only after owner visual PASS on PCC + Text/Image
```

**Post-E2E modules only:** second channel · Analytics · Optimization · Knowledge · Billing/Team · CRM · Legal/Finance/Programmer. **Not now:** HR · CRM · Legal as fillers.

### PRODUCT-02 (OWNER-FROZEN 2026-08-02)

| Doc | Path |
|-----|------|
| Index | `docs/product/PRODUCT-02-INDEX.md` |
| Charter | `docs/product/PRODUCT-02-CHARTER.md` |
| Lifecycle | `docs/product/PROJECT-LIFECYCLE.md` |
| Spine | `docs/product/COMMERCIAL-SPINE.md` |
| Capability cards | `docs/product/CAPABILITY-CATALOG.md` |
| Artifacts | `docs/product/ARTIFACT-FLOW.md` |
| Topology | `docs/product/TOPOLOGY-DECISIONS.md` |
| Owner freeze | `docs/product/OWNER-FREEZE.md` |

**Status:** Blueprint **OWNER-FROZEN**. Architecture agreed ≠ build-everything backlog.

### Owner roadmap decision (2026-08-02 → OWNER-FROZEN)

```
PRODUCT-01 Commercial UX ✅
        ↓
PRODUCT-02 Commercial Product Blueprint  ← OWNER-FROZEN
        ↓
PRODUCT-03 Strategy Architecture  ← OWNER-FROZEN
        ↓
PRODUCT-04-EXECUTION-MODEL  ← OWNER-FROZEN
        ↓
PRODUCT-04-EXECUTION-FABRIC  ← OWNER-FROZEN (2026-08-02)
        ↓
PRODUCT-04-LAUNCH-DOMAIN-MODEL-01  ← docs_draft
        ↓
PRODUCT-04-LAUNCH-DOMAIN-MODEL-AUDIT-01  ← PASS · freeze rec B
        ↓
OD-LDM-01…08 OWNER-APPROVED
        ↓
PRODUCT-04-LAUNCH-DOMAIN-MODEL-PATCH-01  ← docs_verified
        ↓
PRODUCT-04-LAUNCH-DOMAIN-MODEL  ← OWNER-FROZEN (2026-08-02)
        ↓
PRODUCT-04-LAUNCH-ARCHITECTURE-01  ← docs_verified
        ↓
PRODUCT-04-LAUNCH-OWNER-DECISION-EXTRACT-01  ← matrix delivered
        ↓
OD-LA-01…10 OWNER-ACCEPTED
        ↓
PRODUCT-04-LAUNCH-ARCHITECTURE-PATCH-01  ← docs_verified · ready_for_owner_freeze
        ↓
PRODUCT-04-LAUNCH-ARCHITECTURE-FREEZE-01  ← OWNER-FROZEN (2026-08-02)
        ↓
PRODUCT-04-CAPABILITY-PATTERN-01  ← docs_verified · ready_for_owner_review
        ↓
PRODUCT-04-CAPABILITY-PATTERN-FREEZE-01  ← OWNER-FROZEN (2026-08-02)
        ↓
PRODUCT-05-CONTENT-ARCHITECTURE-01  ← draft · docs_verified · ready_for_owner_review
        ↓
OD-CT-01…08 OWNER-APPROVED (all A)
        ↓
PRODUCT-05-CONTENT-ARCHITECTURE-PATCH-01  ← docs_verified · ready_for_owner_freeze
        ↓
PRODUCT-05-CONTENT-ARCHITECTURE-FREEZE-01  ← OWNER-FROZEN (2026-08-02)
        ↓
PRODUCT-06-VISUAL-ARCHITECTURE-01  ← Next priority · NOT STARTED (await TZ)
        ↓
PRODUCT-07-PUBLICATION-ARCHITECTURE-01  ← after Visual freeze
        ↓
Architecture phase CLOSED (no further docs-only architecture programs)
        ↓
Research Evidence Hardening ≥2026-08-18 → owner real research → Runtime R1–R6
```

**Not now:** Settings · Billing · Team · HR · CRM · Legal · Strategy Runtime early · Research before 2026-08-18 · new foundation · Asset Framework · Orchestrator · extra architecture packs after P07 · Factory as Architecture-canonical · H2.7 merge · Image/Video Runtime until Text owner PASS · Publication execute.

### PRODUCT-01.5 capability registry (2026-08-01)

| Field | Value |
|-------|-------|
| **Registry** | `web/src/lib/product-capabilities/` — single SoT for IA availability, nav, home intents, legacy redirects |
| **Public nav** | Unchanged: Home · Projects · Settings (derived from registry) |
| **Available capabilities** | `workspace.home`, `workspace.projects`, `settings.general`, `project.intake`, `project.research` (panel), `launch.content` (INTERNAL_ONLY → `/workspace?view=content_director`) |
| **Reserved/planned** | Strategy, Launch (parent), Visuals, Publication, Analytics, Knowledge (public), Billing, Team, HR, Legal, Programmer, Finance, CRM |
| **Internal** | review, assistant, channels, assets, knowledge route (dev env + flag only) |
| **Preview account** | `owner.slice-e.preview@marketsynth.local` **deleted**; credentials removed from repo |
| **Audit** | `docs/product/PRODUCT-01.5-CAPABILITY-REGISTRY-AUDIT.md` |
| **Verification report** | `docs/product/PRODUCT-01.5-CAPABILITY-REGISTRY-VERIFICATION.md` |

**Verification (2026-08-01 gate):** typecheck PASS; unit **56/56** (registry **15/15**); prod build PASS; capability E2E **10/10** (0 skips); production-boundary **8/8**; Slice E **16/16**; A–D **12/12**; RUNTIME-01F **7/7**; RUNTIME-01G **8/8**; BIV recovery **7/7**; credential grep PASS; real research **not run**.

| **Slice F Landing** | **`automated_verified`** — report `docs/product/PRODUCT-01.4-SLICE-F-LANDING-VERIFICATION.md`; owner visual **NOT SET** |

### PRODUCT-01.4 Slice F Landing (2026-08-01)

| Field | Value |
|-------|-------|
| **Landing** | 8-section public surface — `web/src/components/brand/public/` |
| **CTA** | Registry `project.intake` via `web/src/lib/landing/public-landing.ts` |
| **i18n** | RU + EN `landing.*` keys |
| **Screenshots** | `web/e2e-artifacts/commercial-ux-slice-f-landing/` |
| **Owner pack** | `docs/product/PRODUCT-01.4-SLICE-F-OWNER-VISUAL-PACK.md` |

**Verification:** unit **66/66**; Slice F E2E **17/17**; full regression matrix green on gate `slice-f-gate-20260801032653`.

### PRODUCT-01.4 commercial foundation (2026-07-31)

| Field | Value |
|-------|-------|
| **Research audit** | `docs/research/PRODUCT-01.4-RESEARCH-PIPELINE-AUDIT.md` — owner funnel 116→40→4→partial |
| **Pipeline fixes** | Publisher-diverse fetch order; `FETCHES_PER_CATEGORY` 3; claim fallback ×2; partial `next_steps` + richer interim copy |
| **Design SoT** | `docs/DESIGN.md` |
| **UX unification** | Slices A–D **`automated_verified`**; **Slice E** **`automated_verified`**; **Slice F** **`automated_verified`**; G/H queued |
| **IA SoT** | `docs/INFORMATION_ARCHITECTURE.md` — **awaiting owner approval** (`owner_canonical_ia`) |
| **Journey SoT** | `docs/COMMERCIAL_USER_JOURNEY_MAP.md` — user scenarios |
| **UI gate** | Journey → IA → DESIGN → implementation (4 steps; 4 questions all Yes) |
| **UI unified** | Partial panel, Projects empty, Home recent empty/list → commercial components |
| **Evidence count delta** | **Not re-measured** — requires new owner run (not incident run) |
| **Out of scope** | Telegram, Launch, HR, Legal, new POST routes, relevance gate softening |

**Verification:** pytest PRODUCT-01.4 + recovery **10/10**; frontend unit **36/36**; typecheck **PASS**; production build **PASS**; commercial UX Playwright **12/12**; recovery E2E **7/7**; screenshots `web/test-results/commercial-ux-a-d-verification/` (14 PNG).

**Next:** Owner re-smoke (same incident run) + optional fresh BIV run to measure evidence uplift.

### PRODUCT-01.3B result delivery recovery (2026-07-31)

| Field | Value |
|-------|-------|
| **Root cause** | ORM bound `status` as native PG enum while Alembic column is `VARCHAR(32)` → `latest-run`/`latest` HTTP 500 |
| **Fix** | Explicit `Column(String(32))` + repository string literals (`biv_run_status_values.py`); frontend typed fetch + cold hydration; Projects BIV enrichment |
| **Migration** | **None** — VARCHAR is intentional contract (Alembic `20260723_0057`) |
| **Owner run verify (read-only)** | project `4ecfb41a-…` · run `90a0d5eb-…` · `latest-run` **200** · `latest` **200** · `result_kind=partial_research` |
| **Investigation lifecycle** | **Deferred** — owner investigation `50379730-…` may remain `active` after terminal partial |

**Verification (2026-07-31):** pytest recovery 6/6 + RUNTIME-01G 7/7; frontend unit 27/27; Playwright recovery 7/7; RUNTIME-01F 7/7; reviewers **5/5 PASS**.

**Next:** Owner re-smoke only — **no new POST /runs**. See session log checklist.

**Deferred after re-smoke:** Investigation `50379730-…` terminalization (runtime-hardening candidate).

---

## Session 2026-07-31 — RESULT-DELIVERY-RECOVERY-01 automated gate accepted

| Field | Value |
|-------|-------|
| **Decision** | Owner accepts **`automated_verified`** for PRODUCT-01.3B-BIV-RESULT-DELIVERY-RECOVERY-01 |
| **`real_pipeline_verified`** | **YES** |
| **`owner_re_smoke`** | **PENDING** |
| **`owner_accepted`** | **NOT SET** |

### Owner re-smoke checklist (incident run — do NOT start new research)

**Cold load (incognito):** `http://localhost:3000/workspace?project=4ecfb41a-b9ef-4b60-aa04-dfd7b6e01ae8`

| Check | Expected |
|-------|----------|
| Partial panel visible | YES |
| Insufficient-evidence state clear | YES |
| Findings / gaps / stop reason | visible |
| No intake fallback | YES |
| No new POST `/runs` | YES |

**Projects:** `http://localhost:3000/workspace/projects`

| Check | Expected |
|-------|----------|
| Card name | **Marketsynth** |
| Lifecycle label | **Результат ограничен данными** |
| Card opens same partial result | YES |

**Owner report template:** re-smoke PASS/FAIL · partial panel · insufficient-evidence · projects label · card deep-link · unexpected new run YES/NO

---

## RUNTIME-01 increment sequence (owner-approved 2026-07-30)

| Increment | Status |
|-----------|--------|
| **01A** Durable in-process lifecycle | **PASS** |
| **01B** Workspace progress polling | **`automated_verified`** |
| **01C** Partial output persistence | **`automated_verified`** |
| **01D** Customer-safe partial-result UI | **`automated_verified`** |
| **01E** Commercial surface freeze + route unification | **`automated_verified`** |
| **01F** Canonical E2E | **`automated_verified`** — verification 2026-07-30 (34 pytest + 7 Playwright + 4 production-boundary) |
| **01G** Owner smoke → `owner_accepted` | **FAIL before research start** (2026-07-30 owner screenshot) — env prep PASS; UX/surface blockers |
| **01G concurrent-run + failure-recovery** | **`automated_verified`** — 2026-07-30 (migration `0065`, pytest 7/7 + regression 41/41, Playwright 8/8, production-boundary 8/8, 01F 7/7); **`owner_real_smoke_ready` = YES**; **`real_pipeline_verified` / `owner_accepted` = NOT SET** |
| **FINDINGS-01** Commercial home patch | **`implemented_pending_owner_recheck`** |
| **FINDINGS-01B** Public landing `/` | **`implemented_automated_verified`** — root route restored; owner re-smoke pending |
| **UX-CORRECTION** Customer surface cleanup | **`automated_verified`** — review + post-submit surfaces; production DOM 8/8; 01F 7/7; finalization 3/3 |

**No parallel program:** surface freeze is **part of 01E**, not a separate track.

### Commercial acceptance framing

| Label | Status |
|-------|--------|
| CMVP.1.1 BIV (`006b087`) | **Historical** owner acceptance only |
| Current PRODUCT-01.3 commercial acceptance | **Superseded / invalidated** by owner rejection 2026-07-24 and re-smoke failures |
| **`owner_accepted` (research golden path)** | **FAIL** — 01G owner smoke stopped at Commercial Home UX (2026-07-30); re-smoke after FINDINGS-01 |

### PRODUCT-01.3A — split status

| Sub-slice | Status |
|-----------|--------|
| **01.3A identity/persistence** | **owner verified PASS** |
| **01.3A full closure** | **deferred** — after RUNTIME-01G |
| **`owner_accepted` (full 01.3A)** | **NOT SET** |

**Active blocker:** **01G** owner re-smoke `/` → `/workspace` → 7-step intake → **review** (no real pipeline until owner PASS).

**01G owner smoke findings (2026-07-30, updated UX-CORRECTION):**
- ~~Developer Workspace link visible~~ — fixed FINDINGS-01
- ~~Recent projects placeholder spam~~ — fixed FINDINGS-01
- ~~Root `/` 404~~ — fixed FINDINGS-01B
- **Review step leaked backend diagnostics** (Project ID, sync state, fingerprint, raw enums) — **UX-CORRECTION patch**
- **Four competing save/submit buttons on review** — **UX-CORRECTION patch** (single «Запустить исследование» + «Вернуться и изменить»)
- Intake/home still prototype-grade typography — **partial UX-CORRECTION** (wizard shell + review; workspace home from FINDINGS-01)

**UX-CORRECTION fix:** customer review contract (`step-review-form.tsx`); `customer-readiness.ts` Russian labels; `IntakeDeveloperDiagnostics` behind `isHomeDeveloperMode()`; intake wizard typography/layout; Russian enum labels in schema; e2e DOM assertions + screenshots `web/e2e-artifacts/ux-correction/`.

**FINDINGS-01 fix:** gate Developer link on `isHomeDeveloperMode()`; filter/map recent projects; widen hero typography/CTA; Playwright 01G suite + screenshots.

**01F architecture (deterministic Level-1):**
- Real browser + frontend + backend + DB persistence
- POST `.../business-idea-validation/runs` only (sync `/run` tracked — must stay 0 in canonical suite)
- Deterministic outcomes via **server-side fixture** (`biv_e2e_deterministic_fixtures` + `scripts/e2e_biv_set_fixture.py`) when `BIV_E2E_DETERMINISTIC_ENABLED=true` — **not** in public HTTP contract
- Legacy `biv-golden-path.spec.ts` → `[legacy sync /run regression]` — excluded from commercial PASS

**01F acceptance correction (2026-07-30):** removed `e2e_deterministic_outcome` from public schema; Playwright binds fixture before scenario; production OpenAPI must not expose test controls.

**Status labels:**
| Label | 01F |
|-------|-----|
| `automated_verified` | **SET** (2026-07-30) |
| `browser_verified` | **`automated_playwright_verified`** (2026-07-30) |
| `real_pipeline_verified` | **NOT SET** — requires separate real-provider smoke |
| `owner_accepted` | **FAIL** (01G UX before research) — re-smoke pending |

**Confirmed facts (2026-07-30):**
- Canonical public entry: Landing/`/` hero + `/workspace` → **7-step intake** → async `/runs` → `/workspace?project=`
- Short BIV inline entry **hidden** from public surface (developer mode retains legacy IntentStartPanel)
- Frozen from public nav: assistant, channels, review, assets, tasks, legacy pipeline (redirect/guard)
- Legacy code **preserved**; not deleted

**Not open until 01G:** PRODUCT-QA-01, Content Factory surface, image/video surface, Launch Pack expansion, legacy code deletion.

---

## Snapshot

| Field | Value |
|-------|-------|
| **Date** | 2026-08-02 |
| **Architecture freezes** | PRODUCT-02 · PRODUCT-03 · PRODUCT-04-EM · PRODUCT-04-FABRIC · Launch Domain · Launch Architecture · Capability Pattern · **PRODUCT-05-CONTENT-ARCHITECTURE** |
| **Active program** | **PROGRAM-CONTENT-01** AI Creative Platform — **OPEN** |
| **Decision Engine** | **FROZEN** |
| **Strategy / Launch / Research Runtime** | **Paused** |
| **Next priority** | **PROGRAM-CONTENT-01-TEXT-ARCHITECTURE-01** (await TZ) |
| **Research Hardening** | **PAUSED** until **2026-08-18** |
| **Last known baseline tag** | `project-freeze-2026-07-22` |
| **Last historical acceptance** | CMVP.1.1 `006b087` · VS.2A `691dccc` · KB-WPL-01 `43e2cab3…` |

---

## Current objective

1. Owner Cursor TZ → **PROGRAM-CONTENT-01-TEXT-ARCHITECTURE-01** (Pattern pack; PRODUCT-05 seed)  
2. Then Visual Architecture inside Creative Platform  
3. Generators / providers / Creative Runtime **only after** domain freezes  
4. Decision Engine remains FROZEN until owner unfreeze (≥ Research Hardening window)

---

## What NOT to work on now

- Strategy Runtime CONTRACTS / Launch Runtime / Research Hardening early  
- Provider wiring / Universal Studio UI before Text(+Visual) architecture freeze  
- New foundation · Asset Framework · Orchestrator  
- Reopening frozen Decision packs / PRODUCT-05 without OD  
- HR · CRM · Legal · Billing · Team as current program  

---

## Session handoff

**Next session:** [15_SESSION_LOG.md](15_SESSION_LOG.md) · **PROGRAM-CONTENT-01 OPEN** · next = Text Architecture TZ · Decision Engine FROZEN · stop
