# Marketsynth — Commercial Information Architecture

> **Single product map** — structure, navigation, URLs, permissions, reserved slots.  
> Task: PRODUCT-01.4-COMMERCIAL-FOUNDATION-01 · Last updated: 2026-07-31  
> **Status:** `owner_canonical_ia` — changes require explicit owner approval

**Companion documents (read in order before any commercial UI change):**

1. [COMMERCIAL_USER_JOURNEY_MAP.md](./COMMERCIAL_USER_JOURNEY_MAP.md) — *what* the user does  
2. **This document** — *where* it lives in the product  
3. [DESIGN.md](./DESIGN.md) — *how* it looks  

Legacy route inventory: [workspace_information_architecture.md](./workspace_information_architecture.md) (superseded by §6 URL contract here).

---

## 0. Four-step gate (mandatory)

```
Business Journey  →  Information Architecture  →  Design System  →  Implementation
```

| Step | Document | Question answered |
|------|----------|-------------------|
| **1. Business Journey** | [COMMERCIAL_USER_JOURNEY_MAP.md](./COMMERCIAL_USER_JOURNEY_MAP.md) | What does the user do? |
| **2. Information Architecture** | **This document** | Where does it live? |
| **3. Design System** | [DESIGN.md](./DESIGN.md) | Which components and tokens? |
| **4. Implementation** | Code + tests | Screen + behavior |

**Cursor may not change commercial UI until steps 1–3 are satisfied for that screen.**

### 0.1 Four questions (all must be Yes)

Before any UI change, answer:

| # | Question | Required |
|---|----------|----------|
| 1 | Does this screen **already exist** in this IA (§1–§6)? | **Yes** |
| 2 | Does this screen **match** a journey stage in [COMMERCIAL_USER_JOURNEY_MAP.md](./COMMERCIAL_USER_JOURNEY_MAP.md)? | **Yes** |
| 3 | Does this screen use the **Design System** ([DESIGN.md](./DESIGN.md) + `web/src/components/commercial/*`)? | **Yes** |
| 4 | After HR / Legal / Billing / Analytics attach, will this screen **remain valid** without nav redesign? | **Yes** |

**If any answer is No → UI change forbidden.** Update Journey Map and/or IA first, then DESIGN.md, then code.

### 0.2 New module workflow

```
New module  →  slot in IA (§3)  →  journey stage (Journey Map)  →  DESIGN components  →  functionality
```

**Not:** new feature → change menu → change Workspace → change Header → global redesign.

---

## 1. Product topology (canonical)

Commercial product is **not** a flat list of features under Workspace. Stages belong to **Projects**; cross-project capabilities sit at **Workspace** level.

```
Workspace (account / operator context)
│
├── Home ........................ command center + project picker
├── Projects .................... index of business initiatives
│   └── Project (single initiative)
│         ├── Intake ............ wizard (pre-project / new project)
│         ├── Research .......... evidence, progress, partial/full result
│         ├── Strategy .......... positioning, audience, CJM (post-verdict)
│         └── Launch ............ rollout container (post-verdict / GO)
│               ├── Content ..... posts, copy, content factory
│               ├── Visuals ..... images, visual brief (frozen until pilot)
│               └── Publication . channels, approval, Telegram send
│
├── Analytics ................... cross-project performance (reserved)
├── Knowledge ................... governed corpus, citations (reserved)
│
└── Settings .................... account, workspace prefs
      ├── Billing ............... plans, usage (reserved)
      ├── Team .................. members, roles (reserved)
      ├── HR .................... future (reserved slot)
      ├── Legal ................. future (reserved slot)
      └── Programmer ............ future dev tools (reserved slot)
```

### 1.1 Layer definitions

| Layer | Scope | User question | Never contains |
|-------|-------|---------------|----------------|
| **Workspace** | Account | What am I working on across projects? | Stage artifacts duplicated per project |
| **Project** | One business idea | Where is *this* idea in the journey? | Billing, Team admin |
| **Stage** | One journey phase | What happened / what next for this stage? | Unrelated project data |
| **Launch substage** | Content / Visuals / Publication | What do I approve and publish? | Research rerun |

### 1.2 Anti-pattern (forbidden topology)

```
❌ Workspace sidebar
     ├── Research
     ├── Analytics
     ├── Content
     ├── Launch
     ├── Telegram
     ├── History
     └── Billing
```

Research, Launch, Content, Publication are **project stages**, not sibling workspace nav items.

---

## 2. Navigation rules

Every UI surface must be classified **before** implementation.

| Type | Definition | Example | Nav visible? |
|------|------------|---------|--------------|
| **Page** | Top-level route with own URL and title | `/workspace/projects`, `/workspace/settings` | Yes (if workspace-level) |
| **Workspace shell** | Persistent layout: sidebar + header + main | All `/workspace/*` | — |
| **Module** | Domain capability with reserved IA slot | Analytics, Knowledge, Launch | Page or project section |
| **Project context** | Same shell, `project` query or path segment | `/workspace?project={id}` | Implicit (no extra nav row) |
| **Project stage panel** | Section inside project command center | Partial research panel | No — stacked on Home |
| **Tab** | Switches view within same page/module | Settings → Profile / Security | In-page only |
| **Drawer** | Overlay panel, mobile nav, filters | Mobile sidebar drawer | Overlay |
| **Modal** | Blocking confirmation / short form | Approve publish | Overlay |
| **Wizard** | Multi-step linear flow | Intake 7 steps | Full-width or dedicated route |

### 2.1 Visibility rules

| Surface class | Public nav | Developer nav | Customer sees |
|---------------|------------|---------------|---------------|
| `CANONICAL_PUBLIC` | Yes | Yes | Yes |
| `PLACEHOLDER` | Reserved label, disabled or honest empty | Optional | When module ships |
| `INTERNAL_ONLY` | No | Yes | Never without dev mode |
| `LEGACY_HIDDEN` | No | Redirect to canonical | Never |
| `REDIRECT` | No | — | Canonical target |

**Canonical public nav (v1):** Home · Projects · Settings only.  
Everything else is **project panels** or **reserved workspace modules**.

### 2.2 Project command center rule

**Primary project UX:** `/workspace?project={id}` — vertical stack of stage panels (Research → Verdict → Launch subtree).

Dedicated paths (`/workspace/projects/{id}/research`, etc.) are **deep links** to the same artifacts — not parallel information architecture.

---

## 3. Future reserved slots

Slots are **named in IA before code**. Implementation may be `PLACEHOLDER` or absent.

| Slot ID | Topology location | Nav group | Status | Notes |
|---------|-------------------|-----------|--------|-------|
| `analytics` | Workspace → Analytics | Insights | 📋 Reserved | Cross-project metrics |
| `knowledge` | Workspace → Knowledge | Library | ⚠️ Shell | Governed corpus |
| `billing` | Settings → Billing | Account | 📋 Reserved | No billing logic in CWF.1 |
| `team` | Settings → Team | Account | 📋 Reserved | RBAC future |
| `hr` | Settings → HR | Account | 📋 Reserved | Out of scope CWF.1 |
| `legal` | Settings → Legal | Account | 📋 Reserved | Out of scope CWF.1 |
| `programmer` | Settings → Programmer | Account | 📋 Reserved | Internal tools |
| `finance` | Settings → Finance | Account | 📋 Reserved | Unit economics surfacing |
| `crm` | Workspace → CRM | Work | 📋 Reserved | Post-pilot; not default |
| `launch.content` | Project → Launch → Content | — | ⚠️ Partial | Review queue |
| `launch.visuals` | Project → Launch → Visuals | — | ⏸ Frozen | VS pilot |
| `launch.publication` | Project → Launch → Publication | — | 📋 Reserved | Telegram |
| `strategy` | Project → Strategy | — | 📋 Reserved | Post-verdict |
| `history` | Projects + timeline panel | — | ⚠️ Partial | Cards + deep links |

**Rule:** adding a row here is an **IA change** (owner-approved), not a drive-by nav PR.

---

## 4. User permissions (target)

v1 is effectively **single Owner**. IA must not assume multi-user UI until Team ships — but slots and copy are reserved.

| Role | Workspace | Project stages | Analytics | Knowledge | Settings | Billing | Team admin |
|------|-----------|----------------|-----------|-----------|----------|---------|------------|
| **Owner** | Full | Full | Full | Full | Full | Full | Full |
| **Manager** | Full | Full | Full | Read | Limited | Read | Invite |
| **Employee** | Assigned projects | Assigned stages | Read | Read | Profile | — | — |
| **Future Team** | Policy-driven | Policy-driven | Policy-driven | Policy-driven | Profile | — | — |

### 4.1 v1 implementation note

Until Team module exists: treat all authenticated customers as **Owner**. Do not expose role-specific nav items without backend enforcement.

---

## 5. Mobile rules

Design every commercial screen **mobile-valid by default** — no desktop-only layouts that block later adaptation.

| Pattern | Mobile behavior | Desktop behavior |
|---------|-----------------|------------------|
| Workspace nav | **Drawer** (`workspace-nav-drawer`) | Fixed sidebar |
| Project command center | Single column, panels stack | `max-w-5xl` centered column |
| Wizard (intake) | Single column steps | Two-column where space allows |
| Data tables | Card list or horizontal scroll | Table |
| Stage panels | Full width, collapsible sections | Same order as desktop |
| Modals | Full-screen sheet on narrow viewports | Centered dialog |
| Action bar | Sticky bottom primary CTA | Inline header actions |

**Forbidden:** fixed multi-column stage layouts without narrow breakpoint; hover-only actions; nav items that exceed drawer capacity without grouping.

---

## 6. URL contract

### 6.1 Canonical URLs (target)

| Purpose | URL | IA type | Status |
|---------|-----|---------|--------|
| Landing | `/` | Page | ✅ |
| Login | `/login` | Page | ✅ |
| Workspace home | `/workspace` | Workspace shell | ✅ |
| Project command center | `/workspace?project={uuid}` | Project context | ✅ |
| Projects index | `/workspace/projects` | Page | ✅ |
| New project intake | `/workspace/projects/new` | Wizard | ✅ |
| Intake review | `/workspace/projects/new/review` | Wizard step | ✅ |
| Settings | `/workspace/settings` | Page | ✅ |
| Billing | `/workspace/settings/billing` | Tab / page | 📋 Reserved |
| Team | `/workspace/settings/team` | Tab / page | 📋 Reserved |
| Analytics | `/workspace/analytics` | Page | 📋 Reserved |
| Knowledge | `/workspace/knowledge` | Page | ⚠️ Shell |

### 6.2 Project stage deep links (canonical pattern)

Pattern: `/workspace/projects/{projectId}/{stage}`

| Stage | URL segment | Maps to panel |
|-------|-------------|---------------|
| Research | `research` | Research / partial / progress |
| Strategy | `strategy` | Strategy (future) |
| Launch | `launch` | Launch container (future) |
| Content | `launch/content` | Content factory |
| Visuals | `launch/visuals` | Visual generation |
| Publication | `launch/publication` | Channels / publish |
| Verdict | `verdict` | Verdict (legacy → redirect to home+project) |

**Preferred customer path:** `/workspace?project={id}` with scroll-to-panel. Deep links for sharing and bookmarks only.

### 6.3 Query parameters (stable contract)

| Param | Scope | Meaning |
|-------|-------|---------|
| `project` | Home | Active project context |
| `intent` | Home | Intent routing (legacy; prefer intake) |
| `owner_preview` | Home | Owner-only feature preview (non-product) |

Do not introduce new query params without updating this table.

### 6.4 Legacy redirects (must preserve)

| Legacy path | Canonical target |
|-------------|------------------|
| `/workspace/tasks` | `/workspace` |
| `/workspace/research` | `/workspace` |
| `/workspace/investigations` | `/workspace` (or project list) |
| `/workspace/projects/{id}/investigation` | `/workspace?project={id}` |
| `/workspace/projects/{id}/verdict` | `/workspace?project={id}` |

Code reference: `web/src/lib/routes/commercial-surface.ts`

### 6.5 Internal-only URLs (developer mode)

Not in public nav: `/workspace/assistant`, `/workspace/review`, `/workspace/channels`, `/workspace/assets`, legacy Alpha pipeline routes.

---

## 7. Screen registry (IA ↔ Journey ↔ Route)

| Screen ID | Journey ref | IA location | Route | Nav |
|-----------|-------------|-------------|-------|-----|
| `home` | J1.2 | Workspace → Home | `/workspace` | ✅ |
| `home.project` | J2–J5 | Project command center | `/workspace?project=` | — |
| `projects.index` | J1.5 | Workspace → Projects | `/workspace/projects` | ✅ |
| `intake.wizard` | J1.4 | Project → Intake | `/workspace/projects/new` | — |
| `research.panel` | J2.* | Project → Research | panel on `home.project` | — |
| `verdict.panel` | J3.* | Project → Research/Verdict | panel on `home.project` | — |
| `launch.panel` | J5.* | Project → Launch | panel on `home.project` | — |
| `content.review` | J6.2 | Launch → Content | `/workspace/review` (internal) | dev |
| `publication.channels` | J8.1 | Launch → Publication | `/workspace/channels` (internal) | dev |
| `analytics.dashboard` | J9.1 | Workspace → Analytics | `/workspace/analytics` | reserved |
| `knowledge.index` | J10.2 | Workspace → Knowledge | `/workspace/knowledge` | reserved |
| `settings.root` | J11.1 | Settings | `/workspace/settings` | ✅ |
| `settings.skills` | J11.1 | Settings → Skills / Integrations | `/workspace/settings/skills` | ✅ |
| `settings.billing` | J11.2 | Settings → Billing | `/workspace/settings/billing` | reserved |
| `settings.team` | J11.3 | Settings → Team | `/workspace/settings/team` | reserved |

---

## 8. Drift register (current vs canonical)

Known gaps to close in future slices — **do not fix by ad-hoc nav expansion**.

| Drift | Current | Canonical IA | Fix slice |
|-------|---------|--------------|-----------|
| Flat nav temptation | Dev items in sidebar | Project stages as panels | UX unification |
| Legacy pipeline routes | `/projects/{id}/verdict` etc. | Redirect to `?project=` | RUNTIME-01E+ |
| Review / Channels top-level | Internal routes | Launch → Content / Publication | CWF publication |
| Intake at `/projects/new` | OK | Project → Intake wizard | — |
| Analytics missing | No route | `/workspace/analytics` reserved | Post-CWF.1 |

---

## 9. Change control

| Change type | Requires |
|-------------|----------|
| New workspace nav item | IA §3 slot + owner approval |
| New project stage | IA §1 + Journey Map §3 |
| New URL | IA §6 + `commercial-surface.ts` |
| New component pattern | DESIGN.md |
| Public nav item | IA §2.1 + E2E golden path update |

**IA changes are product decisions**, not implementation details.

---

## 10. References

- [COMMERCIAL_USER_JOURNEY_MAP.md](./COMMERCIAL_USER_JOURNEY_MAP.md)
- [DESIGN.md](./DESIGN.md)
- [MARKETSYNTH-PLATFORM-MAP.md](./product/MARKETSYNTH-PLATFORM-MAP.md)
- [PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md](./product/PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md)
- [web/src/lib/routes/commercial-surface.ts](../web/src/lib/routes/commercial-surface.ts)
