# Changelog

> Chronological record — **one entry per development session**. Never rewrite history.  
> Newest first.

---

# Changelog

> Chronological product/engineering changes. Newest first.

---

## 2026-08-03 — WORKSPACE-BOOT-RECOVERY-02

- Root cause: soft `router.replace` to `?project=` left boot pending; prior band-aid used `location.replace` + 6s timer (forbidden)
- Fix: `workspace-boot.ts` state machine · timed projects fetch (8s) · error+retry UI · inline `bootProjectId` for PCC while URL catches up · soft replace once · no self-redirect
- Removed hard navigation / redirect timeout from workspace home boot path
- Tests: unit `workspace-boot.test.ts` · Playwright `workspace-boot-recovery.spec.ts` **8/8**
- Screenshots: `web/e2e-artifacts/workspace-boot-recovery-02/`
- Note: production `next start` must be **rebuilt** after web changes (stale bundle hid the fix)
- Status: **automated_verified** · owner_visual_ready **YES** · owner_accepted **NOT SET**
- Video Runtime: **NOT STARTED**

## 2026-08-03 — COMMERCIAL-PROJECT-START-01

- Post-login/register entry: 1 project → PCC; N → projects list; 0 → intake
- **Bare `/workspace` (Главная) redirects to commercial entry** — BIV marketing hero («Проверить мою идею») is no longer the start screen
- PCC header: master Marketsynth logo on dark brand block + caption; General then function menu
- Function menu title/hint; skills chips below grid
- Tests: workspace-entry unit · Playwright `commercial-project-start.spec.ts` 1/1 (incl. Home redirect)
- Screenshots: `web/e2e-artifacts/commercial-project-start-01/`
- Status: **automated_verified** · owner_visual_ready **YES** · owner_accepted **NOT SET**
- Video Runtime: **NOT STARTED**

## 2026-08-03 — PROJECT-COMMAND-CENTER-CANONICAL-01

- Canonical `/workspace?project={id}` Project Command Center: brand header · General (recommend-only, `ChatSessionEntrypoint.PROJECT_GENERAL`) · registry-driven capability grid · activity/recent/attention
- APIs: `GET/POST …/command-center` (+ `/general`, `/general/messages`); no provider generation from PCC/General
- Exclusive PCC when `?project=` (Home BIV gated); CD only via `view=content_director` (+ `mode=` / `type=` alias); Projects primary → PCC, secondary → CD
- Tests: pytest `tests/test_project_command_center_canonical.py` 10/10 · typecheck · Playwright `project-command-center-canonical.spec.ts` 1/1
- Screenshots: `web/e2e-artifacts/project-command-center-canonical-01/`
- Composite review: 5/5 PASS (after Research honesty in Recent + execute-spy locks)
- Status: **automated_verified** · owner_visual_ready **YES** · owner_accepted **NOT SET**
- UX-INTEGRATION-01 remains **FAILED_OWNER_VISUAL**; REGRESSION-FIX superseded; Video Runtime **NOT STARTED**

## 2026-08-03 — PROGRAM-CONTENT-01-UX-INTEGRATION-01-REGRESSION-FIX

- **UX-INTEGRATION-01** = **FAILED_OWNER_VISUAL** (Content Hub replaced Project Command Center)
- Root cause: `workspace-home-view` rendered `ProjectContentHub` as root when `?project=` and suppressed intake/home, so fresh projects showed Content-only
- Fix: `ProjectCommandCenter` shell (Overview/Research/Strategy/Launch/Content) · Hub = compact section · CTA opens `view=content_director`
- E2E + screenshots: `web/e2e-artifacts/content-ux-regression-fix/`
- Status: **automated_verified** · owner_visual_ready **YES** · owner_accepted **NOT SET**
- Video Runtime: **NOT STARTED**

## 2026-08-03 — PROGRAM-CONTENT-01-UX-INTEGRATION-01 (project-centric Content)

- Restored commercial model: Content lives inside Project, not as Home generator
- Home: primary CTA «Проверить идею»; small «Новые возможности» teaser → open project (no «Создать материалы» banner)
- Project Command Center: Content Hub (Текст / Изображения / Видео-soon / история)
- Content Director: always shows project name + lifecycle status + honest Strategy/Launch empty states; back → project
- Registry: `project.content_director` canonicalName → Project Content (still project-scoped; not sidebar product)
- Removed: `project-content-director-entry` + Create materials from projects list / recent
- E2E walkthrough + screenshots: `web/e2e-artifacts/content-ux-integration-01/`
- Verification: registry 16 · typecheck · Playwright 1/1 · composite 5/5 PASS after status honesty fix
- Status: later **FAILED_OWNER_VISUAL** — Hub was mistakenly root project screen (see REGRESSION-FIX)
- Video Runtime: not started

## 2026-08-03 — PRODUCT-CD-RUNTIME-02 status correction + OWNER-VISUAL-DELIVERY-RECOVERY

- **Rollback:** premature `OWNER-ACCEPTED` → **automated_verified**; `owner_visual_acceptance` / `owner_accepted` = **NOT SET**
- Reason: automated tests ≠ owner-visible delivery in live browser
- Delivered: public `project.content_director` · CTA «Создать материалы» on project workspace / projects list / recent · Content Director home (Текст / Изображение)
- Pack: `docs/product/PRODUCT-CD-RUNTIME-02-OWNER-VISUAL-PACK.md`
- E2E entry PASS; `owner_visual_ready=YES`; `owner_accepted` still **NOT SET**
- Video Foundation / live paid image smoke: **not started**
- **Superseded for entry UX** by UX-INTEGRATION-01 (project-centric hub)

## 2026-08-03 — PRODUCT-CD-RUNTIME-02 Image Golden Path (status note)

- Prior mistaken OWNER-ACCEPTED rolled back same day
- Code contour remains **automated_verified** (pytest 16 · deterministic E2E · composite 5/5)
- `live_image_provider_verified` = **NOT SET**

## 2026-08-02 — PRODUCT-CD-RUNTIME-02 Image Golden Path (`implemented_verified` → automated_verified)

- Visual Director: VisualRequest → Snapshot → VisualRun → ImageCandidate (1..4) → approve → ImageAsset + cold restore
- API `/projects/{id}/visual-director/*` including authenticated candidate content download
- Provider: `openai_images` (H2.6A gate); deterministic fixture via `CONTENT_DIRECTOR_IMAGE_DETERMINISTIC` (tests/E2E only)
- Storage: `{IMAGE_GENERATION_STORAGE_DIR}/cd-image/{owner}/{project}/{asset}/v{n}.png` — checksum/mime; no base64 in DB
- Skill: `marketsynth.visual_generation` + SkillRun lineage `cd-visual-{run_id}`
- UI: Content Director Text|Image mode switch; no Launch Visuals; no `owner_preview`
- Migration `20260802_0068`; pytest 16; Playwright deterministic E2E + screenshots `web/e2e-artifacts/content-director-image/`
- Fixes after review: single approve pin lock; stale approve blocked; skill_id outside sanitize allowlist
- Composite review **5/5 PASS**

## 2026-08-02 — PROGRAM-CONTENT-01-SKILL-RUNTIME-01 Product Skill Runtime (`OWNER-ACCEPTED`)

- Product Skill Runtime: import → validate → versioned `ProductSkillManifest` → permissioned run (no ZIP subprocess)
- Built-ins: Copywriter (instruction) · XMLRiver Wordstat (integration, existing `XMLRIVER_*`) · Avito (`installed_unconfigured`)
- API `GET /skills`, `POST/GET .../skills/runs`; migration `20260802_0067`
- Content Director uses Copywriter prompts + stamps `skill_id`/`skill_version` + SkillRun lineage
- UI `/workspace/settings/skills`; IA `settings.skills`
- Fix: client `getApiBaseUrl` uses literal `NEXT_PUBLIC_*` (dynamic env was ignored in browser)
- Tests: pytest skill suite + CD; Playwright skills list PASS
- Status: **OWNER-ACCEPTED** (2026-08-02)

## 2026-08-02 — PRODUCT-CD-RUNTIME-01 Text Golden Path (`OWNER-ACCEPTED`)

- Content Director Runtime: ContentRequest / InputSnapshot / ContentRun / candidates as ContentAssets (`telegram_post`)
- API `/projects/{id}/content-director/*`; UI `/workspace?project=&view=content_director`
- Pin-aware text adapter; deterministic fixture opt-in via `CONTENT_DIRECTOR_DETERMINISTIC`
- Post-approve generate blocked (409); failed runs terminal; Factory/H2.7/owner_preview not commercial entry
- Migration `20260802_0066`; pytest 9; Playwright golden path + screenshots; composite 5/5 PASS
- Status: **OWNER-ACCEPTED** (2026-08-02); next was CD-RUNTIME-02 Image (this session)

## 2026-08-02 — PRODUCT-05-CONTENT-ARCHITECTURE-PATCH-01 (docs_verified · ready_for_owner_freeze)

**Session:** PRODUCT-05-CONTENT-ARCHITECTURE-PATCH-01  
**Type:** Docs-only OD application.  
**OD-CT-01…08:** OWNER-ACCEPTED (all **A**).  
**Result:** Soft findings closed (Factory adapter-only · H2.7 isolated · status adapter mapping · owner_preview legacy · Request-first Runtime order · MVP telegram_post · candidates 1..N · approved immutability). Pack = **ready_for_owner_freeze**; `owner_freeze` **NOT SET**.  
**Changed:** 6× `docs/product/PRODUCT-05-CONTENT-*.md` · SoT 00/05/06/15.  
**Code / Runtime:** None · Content Runtime NOT STARTED.  
**Next:** Owner sets OWNER-FROZEN → PRODUCT-06-VISUAL-ARCHITECTURE-01 (owner kickoff). No auto-freeze.

---

## 2026-07-30 — RUNTIME-01G UX-CORRECTION finalization (`automated_verified`)

**Session:** PRODUCT-01.3B-RUNTIME-01G-UX-CORRECTION-FINALIZATION  
**Result:** production-boundary **8/8**; unit **17/17**; typecheck pass; 01F **7/7**; UX finalization **3/3**; backend 01A/01C/01F pytest **34/34**.  
**Fixes:** `BusinessValidationDeveloperPanel` gated on `isHomeDeveloperMode()`; removed `data-biv-state` from customer DOM; post-submit DOM assertions + screenshots in `web/e2e-artifacts/ux-correction/`.  
**Status:** `automated_verified`; `owner_accepted` NOT SET; `real_pipeline_verified` NOT SET.

---

## 2026-07-30 — RUNTIME-01G UX-CORRECTION canonical customer surface cleanup

**Session:** PRODUCT-01.3B-RUNTIME-01G-UX-CORRECTION  
**Problem:** Review step exposed backend diagnostics (IDs, sync, fingerprint, raw enums) and four competing save/submit actions; intake felt like developer console.  
**Fix:** Customer review summary + single primary CTA «Запустить исследование»; secondary «Вернуться и изменить»; autosave copy only; diagnostics in collapsed `IntakeDeveloperDiagnostics` (`isHomeDeveloperMode()` only); Russian option labels; wizard typography/layout pass.  
**Verification:** unit 17/17; Playwright UX-CORRECTION 3/3; regression 01E/01G/FINDINGS-01B green; screenshots `web/e2e-artifacts/ux-correction/`. Production DOM test added (`runtime-01g-ux-correction-production.spec.ts`).  
**Status:** `implemented_pending_owner_recheck` — **no `owner_accepted`**, **no real pipeline run**.

---

## 2026-07-30 — FINDINGS-01B restore canonical public landing `/`

**Session:** PRODUCT-01.3B-RUNTIME-01G-FINDINGS-01B  
**Root cause:** `/` served `(internal)/page.tsx` inside AppShell (ops dashboard), not dedicated public route; no `app/page.tsx`.  
**Fix:** `app/page.tsx` + `PublicLandingView` reusing `MarketsynthHomeHero`; internal dashboard moved to `/dashboard`.  
**Verification:** FINDINGS-01B e2e 7/7, production-boundary 5/5 (incl. GET / 200), 01E landing CTA green.  
**Next:** owner re-smoke `/` then `/workspace` — no real pipeline.

---

## 2026-07-30 — RUNTIME-01G owner smoke FAIL + FINDINGS-01 commercial home patch

**Session:** PRODUCT-01.3B-RUNTIME-01G-OWNER-SMOKE-FINDINGS-01  
**Owner smoke:** **FAIL before research** — Commercial Home UX unacceptable (Developer link leak, garbage recent projects, typography).  
**Fix:** Developer Workspace link gated on `isHomeDeveloperMode()`; commercial recent-project filter; canonical home UI patch.  
**Verification:** unit 15/15, Playwright 01G 5/5, 01E 6/6. Screenshots: `web/test-results/runtime-01g-commercial-home-*.png`.  
**Status:** `owner_accepted` = **FAIL**; `real_pipeline_verified` NOT SET; **owner re-smoke pending**.

---

## 2026-07-30 — RUNTIME-01F verification (`automated_verified`)

**Session:** PRODUCT-01.3B-RUNTIME-01F-VERIFICATION  
**Result:** pytest 34/34, Playwright 7/7, production-boundary 4/4; five reviewers PASS (Test: execution evidence in session log).  
**Status:** `automated_verified`, `browser_verified` = `automated_playwright_verified`; `real_pipeline_verified` / `owner_accepted` NOT SET.  
**Next:** **01G** owner smoke.

---

## 2026-07-30 — RUNTIME-01F canonical golden path E2E (implementation)

**Session:** PRODUCT-01.3B-RUNTIME-01F — Canonical 7-Step Golden Path End-to-End Verification  
**Commercial result:** Single canonical Playwright harness (`runtime-01f-canonical-golden-path.spec.ts`) — Landing → 7-step intake → async `/runs` → verdict / partial / technical failure with refresh/restore. Legacy `biv-golden-path.spec.ts` reclassified as sync `/run` regression only.

**Fixture boundary:** `BIV_E2E_DETERMINISTIC_ENABLED` + server-side `biv_e2e_deterministic_fixtures` table (development/test only). Commercial POST `/runs` unchanged — no test fields in public contract. Real backend + persistence; not mock-only network stubs.

**Acceptance correction:** removed `e2e_deterministic_outcome` from contracts/OpenAPI; Playwright uses `scripts/e2e_biv_set_fixture.py bind` before browser scenario.

**Verification (owner run):** `uv run pytest tests/test_runtime_01f_canonical_golden_path.py tests/test_runtime_01a_biv_durable_lifecycle.py tests/test_runtime_01c_partial_output.py -q`; `npm run test:e2e:runtime-01f` with backend env `BIV_E2E_DETERMINISTIC_ENABLED=true`.

**Status:** implementation complete; `automated_verified` / `browser_verified` pending green runs. `real_pipeline_verified` NOT SET.

**Next:** 01F verification → **01G** owner smoke.

---

## 2026-07-30 — RUNTIME-01E developer-mode security boundary (`automated_verified`)

**Session:** RUNTIME-01E security/product clarification — developer-mode boundary  
**Fix:** `marketsynth.home.developer_mode.v1` no longer bypasses commercial surface freeze in production builds. Effective developer mode requires `NODE_ENV !== "production"` **and** localStorage flag. `/workspace/developer` guarded by environment in production. Workspace research start uses async `POST .../runs` (not sync `/run`). Unguarded legacy pipeline routes wrapped. CORS :3001 reverted.

**Verification:** unit 12/12 (`npm run test:unit`); Playwright dev + production-boundary on :3000; typecheck pass.

**Next:** RUNTIME-01F — canonical E2E.

---

## 2026-07-30 — RUNTIME-01E commercial surface freeze (`automated_verified`)

**Session:** PRODUCT-01.3B-RUNTIME-01E — Commercial Surface Freeze and Canonical Route Unification  
**Commercial result:** Single public Golden Path — Landing CTA → 7-step intake → async research → verdict/partial on `/workspace`. Legacy/frozen surfaces hidden or redirected; code preserved.

**Verification:** pytest 17/17; web typecheck pass; unit 29/29; Playwright spec `runtime-01e-commercial-surface.spec.ts` added.

**Next:** RUNTIME-01F — canonical E2E.

---

## 2026-07-30 — RUNTIME-01D customer-safe partial research UI (`automated_verified`)

**Session:** PRODUCT-01.3B-RUNTIME-01D — Customer-safe Partial Research UI  
**Commercial result:** Terminal partial research renders honest customer panel (findings, sources, gaps, stop reason, remediation, rerun) without verdict/Launch/spinner; refresh hydrates via persisted run + local terminal hint.

**Verification:** pytest 17/17 (01c+01a); web typecheck pass; frontend unit 25/25. Five-reviewer composite PASS.

**Next:** RUNTIME-01E — route unification + commercial surface freeze.

---

## 2026-07-30 — RUNTIME-01C partial research output (`automated_verified`)

**Session:** PRODUCT-01.3B-RUNTIME-01C — evidence-insufficiency partial delivery + governance first application  
**Commercial result:** Failed runs with real research artifacts persist structured partial output (`status=failed`, `output!=null`, no verdict/report).

**Verification:** pytest 17/17 (01c+01a); web typecheck pass; frontend unit 8/8. Five independent governance reviewers + composite PASS after partial UI terminal-state fix.

**Governance:** CURSOR-GOVERNANCE-01 validated on this diff (`automated_verified`).

**Next:** RUNTIME-01D — customer-safe partial UI panel.

---

**Session:** Native Cursor planning/review/security governance — no product code  
**Result:** Planning Gate, 5 read-only reviewer subagents, composite-review skill, delivery report rule, prompt hooks, ops doc  
**Product priority unchanged:** RUNTIME-01C remains active implementation target

**Added:** `.cursor/rules/marketsynth-planning-gate.mdc`, `marketsynth-delivery-report.mdc`, `.cursor/agents/marketsynth-*-reviewer.md`, `.cursor/skills/marketsynth-composite-review/`, `.cursor/hooks.json`, `docs/cursor/CURSOR-GOVERNANCE.md`

**Superpowers:** not installed — owner may trial `/add-plugin superpowers` separately with pin/rollback

---

**Session:** PRODUCT-01.3B-RUNTIME-01C — evidence-insufficiency partial delivery  
**Commercial result:** Failed runs with real research artifacts now persist structured partial output instead of `output=null`.

**Contract:** `status=failed`, original `error_code`, `result_json` with `result_kind=partial_research`, `research_terminal_state=succeeded_insufficient`, verdict fields null.

**Key files:** `partial_research_delivery.py`, `skill.py`, `business_idea_validation_service.py`, `output_enrichment.py`, frontend polling/workspace handlers, `tests/test_runtime_01c_partial_output.py`

**Next:** RUNTIME-01D — customer-safe partial UI panel.

---

**Session:** Full commercial product inventory audit; owner approval with amendments  
**Code changed:** **NONE**  
**Next implementation:** **RUNTIME-01C only**

**Owner decisions:**
1. No separate PRODUCT-SURFACE-FREEZE program — surface freeze merged into **RUNTIME-01E**
2. CMVP.1.1 = historical acceptance; current commercial acceptance invalidated until **01G**
3. Legacy short BIV + sync `/run` = **PARTIAL/LEGACY** (not BROWSER_READY)
4. Projects list = **PARTIAL/REWORK** until hydration E2E proven
5. Legacy E2E: migrate invariants first; no auto-archive
6. Sequence locked: **01C → 01D → 01E → 01F → 01G**
7. After 01G: choose **either** Offer/Launch Pack **or** Telegram text — not Content+Image+Video

**SoT updated:** `00_INDEX`, `05_ROADMAP`, `06_CURRENT_STATE`, `13_KNOWN_PROBLEMS`, `15_SESSION_LOG`

---

## 2026-07-30 — RUNTIME-01B workspace progress polling (`automated_verified`)

**Session:** Golden Path async `/runs` + Workspace polling + refresh recovery  
**Status:** `automated_verified` — not `owner_accepted`  
**Next:** RUNTIME-01C partial output on insufficient evidence

**Delivered:**
- 7-step Golden Path: `POST .../business-idea-validation/runs` (202) instead of blocking sync `/run`
- After 202: persist `run_id` + active session; navigate to `/workspace?project={id}` without waiting for terminal
- Workspace: poll `GET .../runs/{run_id}/progress` (lightweight) + `GET .../runs/{run_id}` (status/output on terminal); backoff 1.5s→4s; stop on terminal
- Refresh recovery via `sessionStorage` `ms_active_biv_research`
- Idempotency + duplicate-submit guard preserved; honest failure incl. `research_execution_interrupted`
- Fix: `resumeStartedRef` race blocked polling on workspace mount

**Verification:** `tests/test_runtime_01a_biv_durable_lifecycle.py` (9) · `research-run-polling.test.ts` + progress/view-model tests · `npm run typecheck` · `e2e/intake-brief-golden-path.spec.ts` (2, not skipped)

**Key files:** `web/src/lib/integration/intake-brief-golden-path.ts`, `web/src/lib/biv/research-run-polling.ts`, `web/src/components/workspace/home/workspace-home-view.tsx`, `web/e2e/intake-brief-golden-path.spec.ts`

---

## 2026-07-30 — RUNTIME-01A durable BIV lifecycle (backend)

**Session:** Implement DB-backed async research run queue + dispatcher + startup recovery  
**Status:** 01A PASS — 9 tests green; frontend unchanged  
**Next:** RUNTIME-01B workspace polling

**Key files:** `app/workers/biv_run_dispatcher.py`, `app/services/business_idea_validation_service.py` (`enqueue_run`, `execute_claimed_run`), `app/api/routes/business_idea_validation.py`, `tests/test_runtime_01a_biv_durable_lifecycle.py`

---

## 2026-07-30 — PRODUCT-01.3B-RUNTIME-01 plan approved

**Session:** Owner approves RUNTIME-01 with two amendments; SoT split clarified  
**01.3A identity/persistence:** owner verified PASS (closed sub-slice)  
**01.3A full closure:** deferred  
**Active:** PRODUCT-01.3B-RUNTIME-01 — implementation next

**Amendments:**
1. No new DB enum — use `failed` + `result_json.research_terminal_state` + partial artifacts
2. True async POST `/runs` → 202 (not frontend background promise)

**Pre-implementation audit:** no BIV worker; run model + idempotency reusable; VARCHAR status (no PG enum)

**Spec:** `docs/product/PRODUCT-01.3B-RUNTIME-01-SPEC.md`

**After PASS:** close route inconsistency → full 01.3A → open 01.3B.2

---

## 2026-07-30 — PRODUCT-01.3A split-verdict + RUNTIME-01 audit

**Session:** Owner re-smoke #3 + runtime audit (no code)  
**01.3A identity/persistence:** PASS (owner verified)  
**01.3A full `owner_accepted`:** NOT SET  
**Active slice:** PRODUCT-01.3B-RUNTIME-01

**Owner re-smoke #3 results:**
- Review: no «Проект не найден» — PASS
- Submit → `/workspace?project={uuid}` — PASS (~5 min sync wait)
- 1 backend project, refresh restore — PASS
- BIV run real (`run_id` created) — PASS start
- Terminal result — FAIL (`high_impact_insufficient_sources`, `output=null`, generic failure UI)

**Closed:** 01.3A-OWNER-FAIL-01/02  
**Opened:** 01.3B-RUNTIME-01 (progress + partial delivery + intake routing audit)

---

## 2026-07-29 — PRODUCT-01.3A-OWNER-FAIL-02

**Session:** Runtime audit + backend project identity contract repair  
**Owner re-smoke:** FAIL (review «Проект не найден»; research not started)  
**Technical verdict:** PASS (automated + E2E); browser_ready — owner re-smoke pending

**Root cause:** Draft carried stale `backendProjectId`; `syncIntakeProject` update path returned terminal `project_not_found` (404) without reconcile or one-time create. Review UI persisted `lastSyncError` before click.

**Completed:**
- `resolveIntakeBackendProjectIdentity`: existing → reconcile by `marketsynth_i2.localDraftId` → clear stale binding → create once → post-bind `fetchProject`
- `verifyIntakeBackendProjectBinding`: review mount clears stale error for recoverable drafts
- Tests: 4 pytest, identity unit test, Playwright 2/2 (provisioned, not skipped)

**Modified files:**
- `web/src/lib/integration/project-sync.ts`
- `web/src/components/project-intake/steps/step-review-form.tsx`
- `tests/test_product_01_3a_owner_fail_golden_path.py`
- `web/src/lib/integration/project-sync.identity.test.ts` (new)
- `web/e2e/intake-brief-golden-path.spec.ts`

**Next:** Owner browser re-smoke on clean new brief; then `owner_accepted` → 01.3B

---

## 2026-07-29 — PRODUCT-01.3A-OWNER-FAIL-01

**Session:** Restore brief submit → BIV golden path  
**Owner smoke:** FAIL (submit → «Проект не найден»)  
**Technical verdict:** PASS (automated); browser_ready — owner re-smoke pending

**Root cause:** Review CTA routed to legacy `/investigation` (I3), not commercial BIV `/workspace`; brief-only buttons never started research.

**Completed:**
- `executeIntakeBriefGoldenPath` orchestration (project → brief → context → confirm → BIV run)
- Workspace navigation with canonical `backend project_id`
- Stale project id re-sync on `alreadyLinked`
- `analysis_requested` → analyzing resume hydration
- Tests: `test_product_01_3a_owner_fail_golden_path.py`, frontend mapping tests, `intake-brief-golden-path.spec.ts`

**Modified files:**
- `web/src/lib/integration/intake-brief-golden-path.ts` (new)
- `web/src/lib/integration/intake-draft-to-analysis-context.ts` (new)
- `web/src/components/project-intake/steps/step-review-form.tsx`
- `web/src/lib/integration/project-sync.ts`
- `web/src/lib/biv/research-hydration-guard.ts`
- `tests/test_product_01_3a_owner_fail_golden_path.py` (new)
- `web/e2e/intake-brief-golden-path.spec.ts` (new)

**Next:** Owner re-smoke brief wizard → research → result; then `owner_accepted` → 01.3B

---

## 2026-07-29 — PRODUCT-01.3A-PRESMOKE-FIX-01

**Session:** Pre-smoke blockers fix before Owner Smoke  
**Verdict:** PASS (automated); browser_ready

**Completed:**
- Migration availability: repair script stamps current code head; verifies `20260724_0060` in chain (head `20260728_0063`)
- Multi-project cold load: `hydrated_unconfirmed` scores above completed legacy project
- Incomplete recovery: «Продолжить» opens prefilled form with missing-field highlights, no dead-end error
- Tests: backend 35/35, typecheck green, frontend unit tests green

**Modified files:**
- `app/domain/alembic_revision_guard.py`
- `scripts/repair_product_01_3a_dev_db.py`
- `tests/test_product_01_3a_backend_availability.py`
- `web/src/lib/biv/pick-analysis-project.ts` (+ test)
- `web/src/lib/biv/recovery-continue.ts` (+ test)
- `web/src/lib/biv/research-hydration-guard.test.ts`
- `web/src/components/workspace/home/workspace-home-view.tsx`

**Unverified:** Playwright `product-01-3a-intake-smoke.spec.ts` — 5 skipped (missing E2E credentials)

**Next:** Owner browser smoke (10 steps) → update SoT with PASS/FAIL

---

## 2026-07-29 — SoT bootstrap

**Session:** Create Project Source of Truth knowledge base  
**Objective:** Enable cold-start project restoration in &lt;5 minutes for any new Cursor session

**Completed:**
- Created `knowledge/00_INDEX.md` through `knowledge/15_SESSION_LOG.md`
- Created scalable subdirs: `decisions/`, `sessions/`, `milestones/`, `audits/`, `research/`
- Seeded decision records, milestone index, audit index, research index
- Populated current state from AGENTS.md + docs (no invented state)

**Modified files:**
- `knowledge/00_INDEX.md` (new)
- `knowledge/01_PROJECT_VISION.md` through `knowledge/15_SESSION_LOG.md` (new)
- `knowledge/decisions/*` (new)
- `knowledge/sessions/*`, `milestones/*`, `audits/*`, `research/*` (new)

**Next recommended task:** PRODUCT-01.3A smoke protocol + owner re-acceptance

---

## Prior history (pre-SoT)

Major accepted milestones before SoT creation — detail in [milestones/](milestones/):

| Date | Event |
|------|-------|
| 2026-07-24 | PRODUCT-01.2 rejected_with_findings |
| 2026-07-24 | KB-WPL-01 closed (hash `43e2cab3…`) |
| 2026-07-22 | VS.2A-P-R accepted (`691dccc`); project freeze tag |
| 2026-07 | CMVP.1 / CMVP.1.1 BIV accepted (`006b087`) |
| 2026 | AI.110–265 marketing/campaign layers frozen |
| 2026 | AI.60–100 publishing/beta frozen |

Full phase history: `docs/phase_ai_*_readiness_audit.md`
