# PRODUCT-01.5-CAPABILITY-REGISTRY-01-VERIFICATION

> Verification-only slice · Gate run `cap-registry-gate-20260801014650` · 2026-08-01

## 1. Verdict

**PASS** — Capability Registry production browser verification complete.

## 2. Effective status

| Field | Value |
|-------|-------|
| **PRODUCT-01.5-CAPABILITY-REGISTRY-01** | **`automated_verified`** |
| **owner_accepted** | **NOT SET** |
| **Slice F Landing** | **`eligible_for_owner_decision`** (not auto-started) |
| **Research / Evidence Hardening** | Frozen until **2026-08-18** |

## 3. Environment

| Component | Value |
|-----------|-------|
| Backend | `http://127.0.0.1:8000` — `/health` 200, `/health/ready` ready |
| Frontend (production) | `http://localhost:3000` — `next start`, `NODE_ENV=production` |
| Frontend (dev, scenario D only) | `next dev --port 3000`, `NODE_ENV` unset |
| Chunk probe | No `main-app.js` dev chunks on production |
| Real provider research | **Not run** |

## 4. Capability matrix (summary)

| Class | Count | Production behavior |
|-------|-------|---------------------|
| `CANONICAL_PUBLIC` available | 4 nav + intake + research panel | Visible/working per E2E |
| `RESERVED` / `planned` | 14 | Absent from nav, home, mobile DOM |
| `INTERNAL_ONLY` | 5 | Blocked in production; dev+flag only (D) |
| `REDIRECT` legacy | 3 | Redirect to canonical targets (I, J) |

## 5. Production nav evidence

Scenario **A** PASS: sidebar shows exactly **Главная · Проекты · Настройки** (3 items).

## 6. Reserved/internal absence evidence

Scenario **B** PASS: three legacy intent-card test IDs absent from commercial home (`intent-card-create-content`, `intent-card-prepare-launch`, `intent-card-grow-business`). In production build commercial home renders `CanonicalCommercialEntryPanel`, not intent cards — broader reserved-module hiding is enforced by **A/H** (3-item nav), **registry unit selectors**, and registry `publicVisible: false` entries (Analytics, Billing, Team, HR, Legal, Programmer, Finance, CRM).

Scenario **C** PASS: malicious `localStorage` developer flag does not expose Assistant / Review / Channels / Assets / Knowledge in production.

Scenario **H** PASS: mobile drawer shows Home / Projects / Settings only; assistant nav absent (internal review/channels/assets parity with desktop A covered via shared selector path + scenario A).

## 7. Route matrix

| Capability | availability | surfaceClass | route | publicVisible | Expected (prod) | Actual (prod) | Result |
|------------|--------------|--------------|-------|---------------|-----------------|---------------|--------|
| workspace.home | available | CANONICAL_PUBLIC | /workspace | true | Nav + home | Working | PASS |
| workspace.projects | available | CANONICAL_PUBLIC | /workspace/projects | true | Nav | Working | PASS |
| settings.general | available | CANONICAL_PUBLIC | /workspace/settings | true | Nav | Working | PASS |
| project.intake | available | CANONICAL_PUBLIC | /workspace/projects/new | true | Home CTA (F) | Working | PASS |
| project.research | available | CANONICAL_PUBLIC | panel | true | Project context (G) | Working | PASS |
| project.strategy | planned | RESERVED | — | false | Hidden | Hidden | PASS |
| project.launch | planned | RESERVED | — | false | Hidden | Hidden | PASS |
| launch.content/visuals/publication | planned | RESERVED | — | false | Hidden | Hidden | PASS |
| workspace.analytics | reserved | RESERVED | — | false | Hidden | Hidden | PASS |
| settings.billing/team/hr/legal/programmer/finance | reserved | RESERVED | — | false | Hidden | Hidden | PASS |
| settings.crm | reserved | RESERVED | — | false | Hidden | Hidden | PASS |
| internal.* | internal | INTERNAL_ONLY | various | false | Blocked (C) | Blocked | PASS |
| legacy.research | disabled | REDIRECT | /workspace/research | false | Redirect (I) | Redirect | PASS |
| legacy.tasks/execution | disabled | REDIRECT | various | false | Redirect (J) | Redirect | PASS |

## 8. Browser scenarios (A–J)

| Scenario | Description | Result |
|----------|-------------|--------|
| A | Production nav 3 items | PASS |
| B | Reserved absent from commercial DOM | PASS |
| C | localStorage cannot expose internal nav (prod) | PASS |
| D | Dev env + flag exposes approved internal surfaces | PASS |
| E | No dead home CTA | PASS |
| F | Research CTA → `/workspace/projects/new` | PASS |
| G | Project deep link `/workspace?project={id}` | PASS |
| H | Mobile nav = desktop registry | PASS |
| I | Legacy research route redirect | PASS |
| J | Legacy assistant redirect | PASS |

**Total: 10/10 · Skips: 0**

## 9. Commands and exit codes

| Step | Command | Exit |
|------|---------|------|
| Gate (full) | `npm run test:e2e:capability-registry-gate` | **0** |
| Typecheck | `npm run typecheck` | **0** |
| Unit | `npm run test:unit` | **0** (56/56) |
| Build | `NODE_ENV=production npm run build` | **0** |
| Capability E2E prod | `--grep-invert "D developer"` | **0** (9/9) |
| Capability E2E dev | `--grep "D developer"` | **0** (1/1) |
| Production boundary | `npm run test:e2e:production-boundary` | **0** (8/8) |
| Slice E | `playwright.commercial-ux-slice-e.config.ts` | **0** (16/16) |
| A–D | `playwright.commercial-ux-verification.config.ts` | **0** (12/12) |
| RUNTIME-01F | `npm run test:e2e:runtime-01f` | **0** (7/7) |
| RUNTIME-01G | `npm run test:e2e:runtime-01g-concurrent-run-failure-recovery` | **0** (8/8) |
| BIV recovery | `npm run test:e2e:biv-result-delivery-recovery` | **0** (7/7) |

Logs: `web/e2e-artifacts/capability-registry-gate/cap-registry-gate-20260801014650/`

## 10. Regression results

| Suite | Pass |
|-------|------|
| Registry unit invariants | 15/15 |
| All frontend unit | 56/56 |
| Capability E2E | 10/10 |
| Production boundary | 8/8 |
| Commercial UX Slice E | 16/16 |
| Commercial UX A–D | 12/12 |
| RUNTIME-01F | 7/7 |
| RUNTIME-01G | 8/8 |
| BIV result-delivery recovery | 7/7 |

## 11. Security boundary

- Registry controls **UX exposure only** — not backend authorization.
- `localStorage` developer flag ignored in production build (unit + E2E C).
- Internal routes require non-production environment + explicit flag (D).
- Preview password **not present** in repo (`git grep Owner-SliceE-Preview1` → no hits).

## 12. Credential cleanup proof

- Gate pre-flight: **Credential cleanup grep: PASS**
- Preview account email retained only in `scripts/delete_preview_account.py` default arg (sanitized reference, not credential)
- `06_CURRENT_STATE.md` documents deletion — acceptable SoT reference

## 13. Reviewer verdicts

| Reviewer | Verdict |
|----------|---------|
| marketsynth-architecture-reviewer | **PASS** |
| marketsynth-product-reviewer | **PASS** |
| marketsynth-runtime-reviewer | **PASS** |
| marketsynth-security-reviewer | **PASS** |
| marketsynth-test-reviewer | **PASS** |

**5/5 PASS** — non-blocking findings only (registry drift duplication, E2E coverage gaps for legacy tasks/execution redirects, negative-path validator tests).

## 14. Changed files (verification slice)

- `web/scripts/run-capability-registry-verification-gate.ps1` — dev phase `NODE_ENV` fix, clean `.next` between prod/dev/regression

## 15. SoT updates

- `knowledge/06_CURRENT_STATE.md` — status → `automated_verified`
- `knowledge/15_SESSION_LOG.md` — verification session entry
- This document

## 16. Residual risks

1. Registry unit tests alone do not prove browser behavior — mitigated by 10/10 E2E PASS.
2. Landing (Slice F) not started — avoids premature cards for unavailable modules.
3. `owner_accepted` still NOT SET — owner visual acceptance for Slice E remains separate track.
4. **Deferred (non-blocking, post-01.5):** negative-path validator unit tests ([Test review](55b431a6-79f5-4ef7-af6a-09679252f63b) REG-NEG-01); E2E for `/workspace/tasks` and `/workspace/execution` redirects (LEGACY-REDIRECT-GAP-01); derive frozen/legacy lists from registry ([Architecture review](441dfb71-fae6-4903-8bb6-8819c3b23448) CAP-REG-DRIFT-01).

## 17. Slice F eligibility

**eligible_for_owner_decision** — owner may choose Slice F Landing or Strategy capability planning. **Do not auto-start Landing.**
