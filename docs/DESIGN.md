# Marketsynth Design System — Commercial UI Foundation

> **Source of Truth** for customer-facing interface.  
> Task: PRODUCT-01.4-COMMERCIAL-FOUNDATION-01 · Last updated: 2026-07-31

## 0. Mandatory gate — before any screen change

**Cursor must not edit a commercial screen until all four steps pass:**

```
1. Business Journey  →  2. Information Architecture  →  3. Design System  →  4. Implementation
```

| Step | Document |
|------|----------|
| 1 | [COMMERCIAL_USER_JOURNEY_MAP.md](./COMMERCIAL_USER_JOURNEY_MAP.md) — *what* |
| 2 | [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) — *where* |
| 3 | **This document** — *how* |
| 4 | Code + tests |

### Four questions (all must be Yes)

1. Screen exists in **INFORMATION_ARCHITECTURE.md**?  
2. Screen matches **COMMERCIAL_USER_JOURNEY_MAP.md**?  
3. Screen uses **this document** + `web/src/components/commercial/*`?  
4. Valid after HR / Legal / Billing / Analytics attach?

**Any No → UI change forbidden.**

If IA lacks the module → update [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) first (owner IA change), then Journey Map, then this file, then code.

**Goal:** no screen work that forces global nav redesign when Launch, Analytics, Billing, or HR attach.

---

## 1. Purpose

Marketsynth is a **commercial SaaS product**. The interface must communicate trust, progress, and next actions — not infrastructure.

This document governs **Commercial surfaces** (CWF.1 Golden Path):

- Public landing `/`
- Commercial Home `/workspace`
- Project intake wizard
- BIV research progress & results (full + partial)
- Projects list
- Settings entry points visible to customers

**Out of scope here:** Agent-chat ops UI (shadcn/light track) until explicit unification slice.

## 2. Principles

1. **Answer four questions on every terminal screen:** What happened? What is proven? What is missing? What next?
2. **No silent refusal** — “insufficient data” always ships explanation, gaps, and steps.
3. **Token-first** — no raw HEX in components; extend `web/src/styles/brand-tokens.css`.
4. **One visual language** — same card, button, empty state, badge on all commercial routes.
5. **Future-ready layout** — slots defined in [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md); shells defined here. No ad-hoc nav expansion.
6. **No wow-chrome** — no glassmorphism, no decorative motion; readability > ornament.

## 3. Token reference

**Canonical file:** `web/src/styles/brand-tokens.css`

| Group | Tokens | Use |
|-------|--------|-----|
| Background | `--ms-bg-canvas`, `--ms-bg-surface`, `--ms-bg-elevated` | Page / card / nested |
| Text | `--ms-text-primary`, `--ms-text-secondary`, `--ms-text-muted`, `--ms-text-on-brand` | Hierarchy |
| Border | `--ms-border-default`, `--ms-border-strong`, `--ms-border-subtle`, `--ms-border-focus` | Cards, inputs |
| Brand | `--ms-brand-primary`, `--ms-brand-secondary` | CTA, links |
| Status | `--ms-status-success/warning/danger/info` | Alerts, badges |
| Domain | `--ms-verdict-*`, `--ms-evidence-*`, `--ms-risk-*` | BIV semantics |

**Aliases (use these, not ad-hoc fallbacks):** `--ms-danger`, `--ms-success`, `--ms-warning`, `--ms-accent`, `--ms-text-on-brand`.

## 4. Typography

| Role | Classes | Example |
|------|---------|---------|
| Page title | `text-2xl font-semibold` | Projects, intake header |
| Panel title | `text-lg font-semibold` | Partial research, verdict |
| Section title | `text-sm font-semibold` | Findings, gaps |
| Body | `text-sm` / `text-base` | Descriptions |
| Caption | `text-xs` | Meta, lifecycle |
| Eyebrow | `text-xs uppercase tracking-wide` | Partial badge |

## 5. Layout

| Shell | Width | Notes |
|-------|-------|-------|
| Commercial Home | `max-w-5xl` | Primary workspace |
| Projects list | `max-w-3xl` | Narrow list (exception) |
| Intake wizard | `max-w-6xl` | Two-column steps |
| Page padding | `px-4 py-8 sm:px-8` | Standard |

Vertical rhythm: `space-y-6` (page sections), `space-y-5` (panel internals).

## 6. Components (canonical)

Location: `web/src/components/commercial/`

| Component | File | Use |
|-----------|------|-----|
| `CommercialCard` | `commercial-card.tsx` | Bordered surface |
| `CommercialCardInset` | `commercial-card.tsx` | Nested callout |
| `CommercialButton` | `commercial-button.tsx` | Primary / secondary CTA |
| `CommercialBadge` | `commercial-badge.tsx` | Lifecycle, status |
| `CommercialEmptyState` | `commercial-empty-state.tsx` | Lists with zero items |
| `CommercialPageHeader` | `commercial-page-header.tsx` | Page / panel titles |
| `CommercialTimeline` | `commercial-timeline.tsx` | Research progress |
| `CommercialLoadingState` | `commercial-loading-state.tsx` | Loading / skeleton |
| `CommercialAlert` | `commercial-alert.tsx` | Failure / notice |
| `CommercialProgress` | `commercial-progress.tsx` | Confidence bars |
| `CommercialStatus` | `commercial-status.tsx` | Lifecycle chips |

**Planned (next slices, do not duplicate ad-hoc):**

- `CommercialInsightCard` — finding / evidence row

## 7. Domain patterns

### 7.1 Research running
- Progress timeline visible
- Stages named in customer language (not backend enums)
- No duplicate POST /runs on refresh

### 7.2 Partial research
- Badge: «Частичный результат»
- Sections (order): interim conclusion → stop reason → established → findings → evidence → gaps → limitations → next steps → actions
- Must show **next steps** from backend `next_steps[]`
- Rerun is explicit user action only

### 7.3 Full verdict
- `BusinessValidationResultCard` — customer report hydrated
- Launch Pack decision when applicable

### 7.4 Technical failure
- `ResearchFailurePanel` — recoverable copy, no stack traces

## 8. Future modules (architectural placeholders)

**Canonical topology, nav, URLs:** [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md).

Do not add sidebar items or routes without an IA §3 slot.

## 9. Accessibility

- `aria-labelledby` on panels
- `role="alert"` on error surfaces
- Focus ring: `--ms-border-focus`
- `prefers-reduced-motion` respected for logo animation

## 10. Anti-patterns (forbidden)

- Raw HEX in TSX (except `brand-tokens.css`)
- New empty-state markup without `CommercialEmptyState`
- Swallowing API 500 as “no research”
- Developer diagnostics on commercial path without `isHomeDeveloperMode()`
- JSON / enum strings in customer UI

## 11. Migration checklist

- [x] Token aliases in `brand-tokens.css`
- [x] Commercial primitives (`commercial/*`)
- [x] Partial panel uses CommercialCard + enriched sections
- [x] Projects empty state uses `CommercialEmptyState`
- [x] Home recent projects empty → `CommercialEmptyState`
- [x] Commercial User Journey Map (`docs/COMMERCIAL_USER_JOURNEY_MAP.md`)
- [x] Commercial Information Architecture (`docs/INFORMATION_ARCHITECTURE.md`)
- [x] Extract `CommercialPageHeader`
- [x] Extract `CommercialTimeline`, `CommercialLoadingState`, `CommercialAlert`, `CommercialProgress`, `CommercialStatus`
- [ ] Intake wizard i18n (hardcoded RU strings)

## 12. References

- **Information Architecture (read before screen work):** [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md)
- **User Journey Map:** [COMMERCIAL_USER_JOURNEY_MAP.md](./COMMERCIAL_USER_JOURNEY_MAP.md)
- Research audit: `docs/research/PRODUCT-01.4-RESEARCH-PIPELINE-AUDIT.md`
- UX audit: `docs/COMMERCIAL_UX_AUDIT.md`
- Product constitution: `docs/HOME_PRODUCT_RULE.md`
- Brand assets: `web/src/lib/brand/product-brand.ts`
