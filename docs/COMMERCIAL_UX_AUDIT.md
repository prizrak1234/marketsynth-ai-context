# Commercial Product UX Audit

> **Task:** PRODUCT-01.4-COMMERCIAL-UX-AUDIT-01  
> **Date:** 2026-07-31  
> **Status:** `slices_a_d_automated_verified` — Slice A–D gate PASS (VERIFICATION-01); E–H pending  
> **SoT references:** [COMMERCIAL_USER_JOURNEY_MAP.md](./COMMERCIAL_USER_JOURNEY_MAP.md) · [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## Unification progress (PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01)

| Slice | Status | Notes |
|-------|--------|-------|
| **A — Foundation** | ✅ **`automated_verified`** | PageHeader, Timeline, LoadingState, Alert, Progress, Status |
| **B — Workspace Home** | ✅ **`automated_verified`** | Progress panel, failure, verdict, launch preview, recent projects |
| **C — Research UX** | ✅ **`automated_verified`** | Partial + verdict + progress + failure unified |
| **D — Projects** | ✅ **`automated_verified`** | PageHeader, Card, Status, Loading, Empty |
| **E — Intake** | ✅ **Implemented** (Slice E) — browser gate pending | Wizard shell, steps, review, form primitives |
| **F — Landing** | ✅ **`automated_verified`** | Public shell, 8 sections, registry CTA, RU+EN, gate 17/17 + regression |
| **G — Settings / Auth** | ⏳ Pending | |
| **H — Cleanup** | ⏳ Pending | |

| Metric | Audit baseline | After A–D |
|--------|----------------|-----------|
| Journey compliance | ~75% | **~82%** |
| IA compliance | ~65% | **~65%** (no route changes) |
| DESIGN compliance | ~15% | **~45%** |
| Research UX | ~70% | **~88%** |
| Overall commercial UX | ~55% | **~72%** (A–D production-browser verified) |

---

## 1. Executive Summary

Marketsynth has a **strong canonical architecture on paper** (Journey → IA → Design) but **uneven implementation**. The golden path (Landing → Intake → Research → Partial/Verdict on Home) is functionally present; guards and redirects protect commercial users from most legacy routes. However:

| Area | Compliance | Risk |
|------|------------|------|
| **Journey Map** | ~75% | Dual intake, legacy pipeline pages, developer-only surfaces leak context |
| **Information Architecture** | ~65% | Public nav correct (3 items); 20+ legacy routes remain; project stages not fully panel-only |
| **Design System** | ~15% | `commercial/*` used on 3 surfaces only; ~57 files use inline card styling |
| **Research UX** | ~70% | Partial panel strong post-01.4; progress/verdict/failure not unified |
| **Future compatibility** | ~60% | Topology supports Launch subtree; flat legacy indexes and dual URLs are debt |

**Verdict:** Product is **commercially usable** on the golden path but **not commercially unified**. Mass screen rework is correctly blocked until this audit and owner IA approval. Next slice: **PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01**.

**Key metrics (implementation scan):**

| Metric | Value |
|--------|-------|
| `(product)` route files | 39 |
| IA canonical public nav items | 3 (Home, Projects, Settings) ✅ |
| Legacy / internal routes still routable | 22+ |
| Files using `CommercialCard` | 4 |
| Files with inline card `borderColor`/`background` | ~57 |
| Files using `CommercialButton` | 3 |
| Files using raw `<button>` in workspace | ~58 |
| `LoadingSkeleton` on product surfaces | 0 |
| `CommercialEmptyState` call sites | 2 |

---

## 2. Journey Compliance

### 2.1 Journey coverage matrix

| Journey | Stages in Map | Implemented | Gap |
|---------|---------------|-------------|-----|
| J1 Discover & start | J1.1–J1.5 | ✅ Landing, Home, Intake, Projects | Dual intake on Home (dev) |
| J2 Research | J2.1–J2.5 | ✅ Progress, partial, failure | Progress not extracted; no dedicated timeline component |
| J3 Verdict | J3.1–J3.3 | ✅ Full + partial | Verdict card not on design system; legacy `/verdicts` index |
| J4 Strategy | J4.* | 📋 | Legacy `/strategies`, `/projects/{id}/strategy` only |
| J5 Launch | J5.* | ⚠️ Partial | Launch pack + offer panels exist; not in Launch container UX |
| J6 Content | J6.* | ⚠️ Internal | `/workspace/review`, `/assets` — dev only |
| J7 Visuals | J7.* | ⏸ | Owner preview paths only |
| J8 Publication | J8.* | 📋 Internal | `/workspace/channels` — dev only |
| J9 Analytics | J9.* | ❌ | No route (IA reserved — correct) |
| J10 History | J10.* | ⚠️ | Projects list + cards; no timeline panel |
| J11 Settings | J11.* | ✅ Settings | Billing/Team routes absent (IA reserved — correct) |

### 2.2 Journey violations

1. **Dual intake (J1.4 vs dev Home form)** — public users → wizard; developer mode → `AnalysisIntakePanel` on Home bypasses 7-step intake.
2. **Parallel verdict journey** — legacy `/workspace/verdicts` and `/projects/{id}/verdict` duplicate J3 on Home.
3. **Intent cards → assistant (J1.3)** — `IntentStartPanel` routes non-BIV intents to assistant; partial/planned intents not honest enough for commercial-only mode.
4. **History as flat indexes** — investigations/verdicts/strategies/implementation pages are list UIs outside project command center.

---

## 3. IA Compliance

### 3.1 Topology compliance

| IA rule | Status | Evidence |
|---------|--------|----------|
| Project stages under Project, not sidebar | ⚠️ Partial | BIV panels on `?project=` ✅; legacy stage URLs still exist |
| Workspace-level: Analytics, Knowledge, Settings | ⚠️ Partial | Settings ✅; Knowledge shell exists (dev); Analytics absent ✅ |
| Launch subtree (Content / Visuals / Publication) | ❌ Not grouped | Review/Channels/Assets are flat dev nav items |
| Public nav = Home · Projects · Settings | ✅ | `PUBLIC_WORKSPACE_NAV` in `commercial-surface.ts` |
| Anti-pattern flat sidebar (Research, Launch, …) | ✅ Avoided in public nav | Dev mode adds 4 internal items |

### 3.2 URL contract compliance

| URL | IA status | Implementation |
|-----|-----------|----------------|
| `/` | ✅ | `app/page.tsx` → `PublicLandingView` |
| `/login` | ✅ | Auth forms |
| `/workspace` | ✅ | `WorkspaceHomeView` |
| `/workspace?project=` | ✅ | Project command center |
| `/workspace/projects` | ✅ | Projects list |
| `/workspace/projects/new/*` | ✅ | 7-step wizard |
| `/workspace/settings` | ✅ | Settings |
| `/workspace/analytics` | 📋 Reserved | Not implemented ✅ |
| `/workspace/settings/billing` | 📋 Reserved | Not implemented ✅ |
| Legacy redirects | ⚠️ | `/research`, `/tasks`, `/execution` redirect; many legacy routes still mount with guard |

### 3.3 IA drift (from IA §8 + audit)

| Drift ID | Severity | Current | Canonical |
|----------|----------|---------|-----------|
| IA-D1 | P0 | 6 per-project pipeline routes | Redirect to `?project=` |
| IA-D2 | P1 | 8 flat workspace indexes (verdicts, strategies, …) | Remove from commercial path or merge into project |
| IA-D3 | P1 | Review/Channels/Assets as top-level dev nav | Launch → Content / Publication subtree |
| IA-D4 | P2 | `/workspace/developer` escape hatch | Keep dev-only; hide link on commercial |
| IA-D5 | P2 | Knowledge in dev nav but IA says reserved | Align visibility with IA §3 |

### 3.4 Future compatibility (Launch, Analytics, …)

| Future module | Sidebar change required today? | Assessment |
|---------------|-------------------------------|------------|
| Launch | No — if panels stay on `?project=` | ✅ Compatible if unified as project stage stack |
| Content / Visuals / Publication | Yes — dev nav must move under Launch mentally | ⚠️ Requires unification slice, not new nav rows |
| Analytics | Add workspace page | ✅ Slot reserved in IA §3 |
| Knowledge | Enable reserved page | ✅ Route exists |
| Billing / Team / HR / Legal | Settings subtree tabs | ✅ IA §1 topology fits |
| Programmer | Settings subtree | ✅ Slot reserved |

**Risk:** If Content/Publication ship as new top-level sidebar items (current dev pattern), **global nav redesign will be required** — violates IA anti-pattern.

---

## 4. Design Compliance

### 4.1 Token usage

| Criterion | Status |
|-----------|--------|
| `--ms-*` tokens on commercial surfaces | ✅ Widespread |
| Raw HEX in components | ⚠️ `agency-analysis-stages.tsx` uses `#15803d`; some fallbacks `#b42318` |
| Typography roles from DESIGN.md §4 | ⚠️ Mixed — intake uses ad-hoc sizes |
| Layout widths (`max-w-5xl`, etc.) | ⚠️ Home ✅; settings `max-w-2xl`; projects `max-w-3xl` |

### 4.2 Component adoption

| DESIGN.md component | Required on | Actual adoption |
|---------------------|-------------|-----------------|
| `CommercialCard` | All bordered surfaces | **3 call sites** (partial, recent, empty) |
| `CommercialButton` | Primary CTA | **2 call sites** (partial, empty) |
| `CommercialBadge` | Lifecycle / status | **1 call site** (partial) |
| `CommercialEmptyState` | List zero states | **2 call sites** (projects, home recent) |
| `CommercialPageHeader` | Planned | **Not implemented** — `SectionCard` / inline headers |
| `CommercialTimeline` | Research progress | **Not implemented** — `AgencyAnalysisStages` ad-hoc |

### 4.3 Design compliance score by surface

| Surface | DESIGN compliant? | Notes |
|---------|-------------------|-------|
| Partial research panel | ✅ Yes | Reference implementation |
| Projects list | ⚠️ Partial | Empty state ✅; cards inline |
| Home recent projects | ⚠️ Partial | CommercialCard ✅; list items inline |
| Verdict card | ❌ No | Inline border + raw buttons |
| Research failure | ❌ No | Inline danger styling |
| Research progress | ❌ No | Inline in `workspace-home-view.tsx` |
| Intake wizard | ❌ No | Tokens yes; no commercial components; hardcoded RU |
| Landing | ❌ No | Separate brand layout; not using commercial/* |
| Auth | ❌ No | Inline forms; no shared auth shell |
| Settings | ❌ No | `SectionCard` local pattern; not commercial/* |

---

## 5. Screen Inventory

For each screen: commercial task → Journey → IA → route → nav → user → next step → DESIGN → UX issues → keep unchanged?

### 5.1 Landing (`/`)

| # | Answer |
|---|--------|
| Commercial task | Convert visitor; explain value; drive login/intake |
| Journey | J1.1 ✅ |
| IA | Page ✅ (IA §6.1) |
| Route | `/` ✅ |
| Nav | Pre-auth; no workspace nav ✅ |
| User opens | Anonymous visitor ✅ |
| Next step | Login or register → intake |
| DESIGN | ❌ No commercial/* |
| UX problems | Separate visual language from workspace; CTA path OK |
| Keep unchanged? | **No** — unify tokens/CTA with `CommercialButton` in unification slice |

### 5.2 Workspace Home (`/workspace`)

| # | Answer |
|---|--------|
| Commercial task | Command center: start work, see project state, act |
| Journey | J1.2, J2–J5 ✅ |
| IA | `home` / `home.project` ✅ |
| Route | `/workspace`, `?project=` ✅ |
| Nav | Home ✅ |
| User | Authenticated owner ✅ |
| Next step | Intake, research, verdict, launch actions |
| DESIGN | ❌ Mostly inline |
| UX problems | 2100+ line view; phase logic complex; dev panels mixed with commercial |
| Keep unchanged? | **No** — decompose + unify panels; structure OK |

### 5.3 Commercial Home

Same as Workspace Home — **one surface**, not a separate route. Audit treats as alias.

### 5.4 Projects (`/workspace/projects`)

| # | Answer |
|---|--------|
| Commercial task | Resume projects; see lifecycle; deep link to result |
| Journey | J1.5, J10.1 ✅ |
| IA | `projects.index` ✅ |
| Route | ✅ |
| Nav | Projects ✅ |
| User | Returning customer ✅ |
| Next step | Open `?project=` |
| DESIGN | ⚠️ Empty ✅; cards inline |
| UX problems | Card styling not `CommercialCard`; lifecycle labels OK |
| Keep unchanged? | **Partial** — cards need unification; structure OK |

### 5.5 Project (`/workspace?project={id}`)

| # | Answer |
|---|--------|
| Commercial task | Single-idea command center |
| Journey | J2–J5 ✅ |
| IA | `home.project` ✅ |
| Route | ✅ |
| Nav | Implicit (no extra row) ✅ |
| User | Owner with active project ✅ |
| Next step | Stage-specific (research → verdict → launch) |
| DESIGN | ❌ Mixed panels |
| UX problems | Panel order correct in principle; visual inconsistency between partial vs verdict |
| Keep unchanged? | **No** — unify panels; topology OK |

### 5.6 Intake wizard (`/workspace/projects/new/*`)

| # | Answer |
|---|--------|
| Commercial task | Collect idea brief before research |
| Journey | J1.4 ✅ |
| IA | `intake.wizard` ✅ |
| Route | 7 steps ✅ |
| Nav | Wizard (no nav row) ✅ |
| User | New project creator ✅ |
| Next step | Confirm → `?project=` + research |
| DESIGN | ❌ |
| UX problems | Hardcoded Russian; raw buttons; no skeleton loading; duplicate step styling |
| Keep unchanged? | **No** |

### 5.7 Research Progress

| # | Answer |
|---|--------|
| Commercial task | Show what system is doing; reduce anxiety |
| Journey | J2.1–J2.2 ✅ |
| IA | `research.panel` (running state) ✅ |
| Route | Panel on Home ✅ |
| Nav | — |
| User | Owner waiting ✅ |
| Next step | Wait → partial or verdict |
| DESIGN | ❌ |
| UX problems | Text + `AgencyAnalysisStages` only; no %/ETA; stages use unicode marks not timeline component; user may not understand depth of work |
| Keep unchanged? | **No** — extract `CommercialTimeline` |

### 5.8 Partial Result

| # | Answer |
|---|--------|
| Commercial task | Deliver honest limited proof + next steps |
| Journey | J2.3 ✅ |
| IA | `research.panel` ✅ |
| Route | Panel ✅ |
| DESIGN | ✅ Reference |
| UX problems | Strongest commercial panel; evidence links OK; could add risk summary section |
| Keep unchanged? | **Mostly yes** — minor polish only |

### 5.9 Verdict (full)

| # | Answer |
|---|--------|
| Commercial task | GO/NO-GO decision with evidence |
| Journey | J3.1 ✅ |
| IA | `verdict.panel` ✅ |
| Route | Panel ✅ |
| DESIGN | ❌ |
| UX problems | `BusinessValidationResultCard` dense; raw buttons; legacy migration branch confuses; launch CTA not visually grouped as next stage |
| Keep unchanged? | **No** |

### 5.10 Research Failure

| # | Answer |
|---|--------|
| Commercial task | Recover from technical/research failure |
| Journey | J2.5 ✅ |
| IA | `research.panel` (failed) ✅ |
| DESIGN | ❌ |
| UX problems | OK copy; styling not aligned with partial panel |
| Keep unchanged? | **No** — align with failure pattern in DESIGN §7.4 |

### 5.11 History

| # | Answer |
|---|--------|
| Commercial task | See past work |
| Journey | J10.1 ⚠️ |
| IA | `history` partial — projects only ✅ |
| Route | `/workspace/projects` (no timeline) |
| UX problems | No project timeline panel; flat legacy indexes duplicate |
| Keep unchanged? | **No** — add timeline panel on project; retire indexes |

### 5.12 Settings (`/workspace/settings`)

| # | Answer |
|---|--------|
| Commercial task | Profile, locale, logout |
| Journey | J11.1 ✅ |
| IA | `settings.root` ✅ |
| DESIGN | ❌ local `SectionCard` |
| UX problems | Dev integration mode visible to some roles; no Billing/Team placeholders |
| Keep unchanged? | **Partial** — add reserved tabs as disabled placeholders |

### 5.13 Authentication (`/login`, `/register`, …)

| # | Answer |
|---|--------|
| Commercial task | Access product |
| Journey | Implicit pre-J1 ✅ |
| IA | Page ✅ |
| DESIGN | ❌ |
| UX problems | No shared auth layout; 127.0.0.1 warning dev-only leak |
| Keep unchanged? | **No** — auth shell in unification |

### 5.14 Global chrome

| Element | Journey | IA | DESIGN | Issues |
|---------|---------|-----|--------|--------|
| **Sidebar** | — | ✅ public 3-item | ⚠️ inline styles | Dev items in developer mode OK |
| **Mobile drawer** | — | ✅ Drawer type | ⚠️ custom | Works; not shared component |
| **Top navigation** | — | Logo → Home ✅ | Inline | No `CommercialPageHeader` |
| **Dialogs** | — | Modal type | N/A on commercial | **None** on golden path — confirmations inline |
| **Loading** | — | — | ❌ | Text only; no skeleton |
| **Empty states** | — | — | ⚠️ | 2/∞ unified |
| **Error states** | — | — | ⚠️ | `CommercialErrorBoundary` ✅; inline elsewhere |
| **Approval panels** | J5.2, J8.2 | Launch | ❌ | `OfferReviewCard`, launch pack — inline |

---

## 6. Component Inventory

### 6.1 Canonical (target) vs actual

| Pattern | Canonical (DESIGN.md) | Actual implementations | Action |
|---------|----------------------|------------------------|--------|
| **Card** | `CommercialCard` | Inline `rounded-xl border` (~57 files), `SectionCard` (settings), shadcn Card (internal) | **Replace** inline on commercial path |
| **Button** | `CommercialButton` | Raw `<button>` (~58), shadcn Button (internal only) | **Replace** on commercial path |
| **Badge** | `CommercialBadge` | Inline spans, offer approved badges | **Unify** |
| **Empty** | `CommercialEmptyState` | `EmptyState` (internal), ad-hoc text | **Replace** ad-hoc |
| **Loading** | Planned skeleton | `LoadingSkeleton` (internal only), `"Загрузка…"` text | **Create** `CommercialLoadingState` |
| **Progress/Timeline** | `CommercialTimeline` (planned) | `AgencyAnalysisStages` | **Replace** |
| **Panel** | `CommercialCard` + sections | 15+ home panels inline | **Unify** |
| **Header** | `CommercialPageHeader` (planned) | `WorkspaceSectionShell`, inline h2 | **Extract** |
| **Alert** | Token-based status | Inline danger/success borders | **Extract** `CommercialAlert` |
| **Dialog** | Modal for confirm | `ConfirmDialog` internal only | **Add** `CommercialConfirmDialog` when needed |

### 6.2 File-level component disposition

| Component / file | Used | Duplicates | Verdict |
|------------------|------|------------|---------|
| `commercial/commercial-card.tsx` | ✅ | — | **Keep — canonical** |
| `commercial/commercial-button.tsx` | ✅ | raw button | **Keep — expand** |
| `commercial/commercial-badge.tsx` | ✅ | inline badges | **Keep — expand** |
| `commercial/commercial-empty-state.tsx` | ✅ | `data/empty-state.tsx` | **Keep — canonical for product** |
| `data/empty-state.tsx` | Internal | CommercialEmptyState | **Keep for internal; deprecate on product** |
| `data/loading-skeleton.tsx` | Internal | — | **Fork → CommercialLoadingState** |
| `workspace/section-shell.tsx` | Settings, legacy sections | PageHeader | **Merge → CommercialPageHeader** |
| `agency-analysis-stages.tsx` | Home progress | Timeline | **Replace → CommercialTimeline** |
| `partial-research-panel.tsx` | Home | — | **Keep — template for panels** |
| `business-validation-result-card.tsx` | Home | — | **Refactor to commercial/*** |
| `research-failure-panel.tsx` | Home | — | **Refactor to commercial/*** |
| `launch-pack-decision-panel.tsx` | Home | — | **Refactor; group under Launch** |
| `offer-review-card.tsx` | Home | — | **Refactor; approval pattern** |
| `intake-wizard-shell.tsx` | Intake | — | **Refactor to commercial/*** |
| `workspace-nav.tsx` | All workspace | — | **Keep structure; token cleanup** |
| `ui/confirm-dialog.tsx` | Internal | — | **Do not use on product until commercial wrapper** |

---

## 7. UX Problems

### 7.1 Critical (P0 — blocks commercial trust)

| ID | Problem | Screen | Impact |
|----|---------|--------|--------|
| UX-P0-1 | Visual inconsistency between partial (polished) and verdict/failure (legacy) | Home | User distrust at most important moment |
| UX-P0-2 | Research progress does not explain depth/stages clearly | Home | "What is happening?" anxiety |
| UX-P0-3 | Dual intake paths (wizard vs dev home form) | Home / Intake | Confusion if dev mode leaks |
| UX-P0-4 | No unified loading skeleton | All product | Perceived slowness, layout shift |

### 7.2 High (P1 — commercial quality)

| ID | Problem | Screen |
|----|---------|--------|
| UX-P1-1 | Intake wizard hardcoded RU, no i18n | Intake |
| UX-P1-2 | Verdict card dense; weak visual hierarchy for GO/NO-GO | Home |
| UX-P1-3 | Launch/Offer panels not visually grouped as "next stage" | Home |
| UX-P1-4 | Projects cards not using design system | Projects |
| UX-P1-5 | Auth pages disconnected from workspace brand | Login |
| UX-P1-6 | Settings uses local SectionCard pattern | Settings |

### 7.3 Medium (P2 — polish)

| ID | Problem |
|----|---------|
| UX-P2-1 | Landing separate from workspace design language |
| UX-P2-2 | Mobile drawer not extracted as reusable component |
| UX-P2-3 | No disabled placeholders for Billing/Team in Settings |
| UX-P2-4 | Legacy English "Investigation Pipeline" on project routes |

---

## 8. Architecture Problems

| ID | Problem | Type |
|----|---------|------|
| ARCH-1 | 22+ legacy routes still mount (guarded) | IA debt |
| ARCH-2 | 6 per-project pipeline URLs parallel to `?project=` | IA debt |
| ARCH-3 | 8 flat workspace indexes (verdicts, strategies, …) | IA anti-pattern |
| ARCH-4 | Content/Publication as top-level dev nav, not Launch subtree | Future breakage |
| ARCH-5 | `workspace-home-view.tsx` monolith (~2100 lines) | Maintainability |
| ARCH-6 | Developer workspace link on commercial home footer | Boundary leak |
| ARCH-7 | No `/workspace/analytics` route (correct) but no placeholder | Future OK |

---

## 9. Design Problems

| ID | Problem |
|----|---------|
| DES-1 | ~14:1 ratio inline cards vs CommercialCard |
| DES-2 | shadcn Button/EmptyState on internal track only — two design tracks |
| DES-3 | Raw HEX `#15803d` in stages component |
| DES-4 | Inconsistent panel title sizes (text-base vs text-lg vs text-xl) |
| DES-5 | Missing CommercialTimeline, CommercialPageHeader, CommercialAlert |
| DES-6 | Approval flows (offer, launch) lack shared Approval Panel pattern |
| DES-7 | DESIGN.md migration checklist ~40% complete |

---

## 10. Commercial Readiness

### 10.1 Golden path readiness

| Step | User-visible | Commercial quality | Blocker |
|------|--------------|-------------------|---------|
| Landing → Login | ✅ | ⚠️ Visual | None |
| Intake → Confirm | ✅ | ⚠️ i18n/hardcoded | None |
| Research run | ✅ | ⚠️ Progress UX | None |
| Partial result | ✅ | ✅ Strong | None |
| Full verdict | ✅ | ⚠️ Visual density | None |
| Offer / Launch branch | ⚠️ Partial | ⚠️ Not grouped | Product scope |
| Telegram publish | ❌ Frozen | — | CWF gate |

### 10.2 Readiness verdict

| Dimension | Score | Notes |
|-----------|-------|-------|
| Functional golden path | **85%** | Works with real pipeline |
| Journey alignment | **75%** | Legacy parallel paths |
| IA alignment | **65%** | Nav OK; routes debt |
| Design unification | **15%** | Early adoption |
| Future-proof nav | **60%** | Topology doc OK; dev nav pattern risky |
| **Overall commercial UX** | **~55%** | Unification slice required |

**Owner re-smoke:** Can proceed on functional grounds; visual unification is separate slice.

---

## 11. Technical Debt

| Category | Items |
|----------|-------|
| **Route debt** | 6 project pipeline routes, 8 section indexes, recovery-preview, tasks |
| **Component debt** | 57 inline card files, 58 raw button files |
| **i18n debt** | Intake wizard hardcoded RU |
| **Monolith debt** | `workspace-home-view.tsx` |
| **Test debt** | No visual regression tests for design system |
| **Doc debt** | IA `owner_canonical_ia` awaiting owner approval |
| **Temporary** | Legacy migration branch in verdict card; developer panels on home |

---

## 12. Prioritized Fix Plan

For **PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01** — ordered to avoid nav redesign.

### Phase A — Design system completion (no route changes)

| Priority | Item | Files | Effort |
|----------|------|-------|--------|
| A1 | Extract `CommercialPageHeader` | new + settings, projects | S |
| A2 | Extract `CommercialTimeline` from `AgencyAnalysisStages` | new + home | S |
| A3 | Extract `CommercialLoadingState` / skeleton | new + home, projects, intake | S |
| A4 | Extract `CommercialAlert` (error/warning/info) | new + failure, boundaries | S |
| A5 | Document approval panel pattern in DESIGN.md | docs | S |

### Phase B — Home panel unification (same IA, same routes)

| Priority | Item | Files | Effort |
|----------|------|-------|--------|
| B1 | Verdict card → commercial/* | `business-validation-result-card.tsx` | M |
| B2 | Research failure → commercial/* | `research-failure-panel.tsx` | S |
| B3 | Research progress → CommercialTimeline | `workspace-home-view.tsx` | M |
| B4 | Launch pack + offer → Launch group visual | `launch-pack-*`, `offer-*` | M |
| B5 | Agency result actions → CommercialButton | `agency-result-actions.tsx` | S |

### Phase C — Secondary commercial surfaces

| Priority | Item | Files | Effort |
|----------|------|-------|--------|
| C1 | Projects cards → CommercialCard | `projects/page.tsx` | S |
| C2 | Intake wizard → commercial/* + i18n | `intake-wizard-shell.tsx`, steps | L |
| C3 | Auth shared shell + CommercialButton | `login-form.tsx`, etc. | M |
| C4 | Settings → commercial SectionCard merge | `settings-page-view.tsx` | M |
| C5 | Landing CTA alignment | `public-landing-view.tsx` | S |

### Phase D — IA debt (requires owner approval, E2E updates)

| Priority | Item | Effort |
|----------|------|--------|
| D1 | Redirect all project pipeline routes → `?project=` | M |
| D2 | Remove or hard-block flat indexes for commercial users | M |
| D3 | Move dev nav Review/Channels/Assets under logical Launch group (dev labels) | S |
| D4 | Add Settings placeholders: Billing, Team (disabled) | S |
| D5 | Project timeline panel on `?project=` (History) | L |

### Phase E — Verification

| Item | Command / criterion |
|------|---------------------|
| Unit tests | `npm run test:unit` |
| Golden path E2E | `npm run test:e2e:runtime-01f` |
| Recovery E2E | `npm run test:e2e:biv-result-delivery-recovery` |
| Production boundary | `npm run test:e2e:production-boundary-gate` |
| Visual regression | Add Playwright screenshots for partial, verdict, projects (new) |
| Owner browser | Cold load partial + projects per checklist |

**Estimated slices:** A+B = one PR; C = one PR; D = one PR (IA-gated); E continuous.

---

## 13. Definition of Done — full commercial unification

Unification is **done** when all criteria pass:

### 13.1 Gate compliance

- [ ] Every commercial screen mapped in Journey Map §3
- [ ] Every commercial screen in IA §7 registry
- [ ] Every commercial screen uses DESIGN.md components (no inline card/button on product path)
- [ ] Four questions (IA §0.1) = Yes for all screens

### 13.2 Design system

- [ ] `CommercialCard`, `Button`, `Badge`, `EmptyState`, `LoadingState`, `PageHeader`, `Timeline`, `Alert` implemented
- [ ] Zero raw HEX in `(product)` components
- [ ] Typography and spacing match DESIGN.md §4–§5
- [ ] Approval panel pattern documented and used for Offer/Launch

### 13.3 IA

- [ ] Public nav remains Home · Projects · Settings only
- [ ] All project stages accessible via `?project=` panel stack
- [ ] Legacy pipeline routes redirect (not parallel UX)
- [ ] Launch subtree visually grouped (Content / Visuals / Publication)
- [ ] Reserved slots visible as placeholders where appropriate (Settings)

### 13.4 Research UX

- [ ] Progress uses CommercialTimeline; user understands stages
- [ ] Partial panel remains reference quality
- [ ] Verdict answers: proven / missing / next
- [ ] Failure panel matches DESIGN §7.4

### 13.5 Future compatibility

- [ ] Adding Analytics = new page only, no sidebar restructure
- [ ] Adding Billing/Team = Settings tabs only
- [ ] Adding Launch content = project panel group, not new top-level nav
- [ ] Owner sign-off on IA frozen

### 13.6 Verification

- [ ] Golden path E2E green
- [ ] Visual regression baseline captured
- [ ] Owner browser PASS on unified surfaces
- [ ] No new POST routes; no business logic change

---

## Appendix A — Route inventory (39 product routes)

| Class | Count | Examples |
|-------|-------|----------|
| Canonical public | 12 | `/`, `/workspace`, `/projects`, `/settings`, intake 7 steps, auth 5 |
| Legacy guarded | 14 | `/assistant`, `/review`, `/verdicts`, `/knowledge`, … |
| Project pipeline legacy | 6 | `/projects/{id}/verdict`, … |
| Redirect only | 3 | `/research`, `/execution`, `/recovery-preview/r3` |
| Developer | 1 | `/workspace/developer` |

## Appendix B — Research UX deep dive

| Element | User understands? | Gap |
|---------|-------------------|-----|
| Research queued | ⚠️ | Minimal copy |
| Stages list | ⚠️ | Unicode marks; no time estimate |
| Evidence list | ✅ | Partial panel good |
| Findings | ✅ | |
| Gaps / limitations | ✅ | Post-01.4 |
| Next steps | ✅ | Post-01.4 |
| Risks | ⚠️ | In verdict card, not partial |
| Recommendations | ⚠️ | Launch CTAs separate visually |
| Retry / refine | ✅ | Agency actions present |

---

## Appendix C — References

- [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md)
- [COMMERCIAL_USER_JOURNEY_MAP.md](./COMMERCIAL_USER_JOURNEY_MAP.md)
- [DESIGN.md](./DESIGN.md)
- [PRODUCT-01.4-RESEARCH-PIPELINE-AUDIT.md](./research/PRODUCT-01.4-RESEARCH-PIPELINE-AUDIT.md)
- `web/src/lib/routes/commercial-surface.ts`

**Next task:** PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01 (Phase A+B first).
