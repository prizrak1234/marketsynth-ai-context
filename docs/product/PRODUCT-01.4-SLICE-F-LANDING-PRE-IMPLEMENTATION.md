# PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01F — Pre-Implementation Check

> **Date:** 2026-08-01 · **Owner decision required:** NO (positioning matches approved PRODUCT_BRAND / task brief)

## 1. Current landing component tree

```
app/page.tsx (server metadata)
└── PublicLandingView (client)
    ├── AuthProvider
    └── LocaleProvider
        └── PublicPageShell
            ├── PublicHeader
            ├── main#main-content
            │   └── CommercialLandingContent (8 sections)
            └── PublicFooter
```

**Before Slice F:** `PublicLandingView` → single `MarketsynthHomeHero` (logo-heavy card, workspace-like panel).

**Legacy duplicate:** `MarketsynthHomeHero` also used in `dashboard-view.tsx` (unchanged).

## 2. Journey ID

**J1.1 Landing** — Understand value → Start intake / Sign in

## 3. IA screen ID

**marketing.landing** (J1.1 public landing)

## 4. Current CTA flow (pre-change)

| State | CTA | Target |
|-------|-----|--------|
| Unauthenticated | «Проверить мою идею» | `/login?next=/workspace/projects/new` |
| Authenticated | same label | `/workspace/projects/new` |

Resolver: `canonicalIntakeHref()` + `loginNextHref()` in hero (not registry selector).

## 5–6. Authenticated / Unauthenticated flows

Unauthenticated: `/` → CTA → login?next=intake → login → intake  
Authenticated: `/` → CTA → intake  
Login `next` sanitized: starts with `/`, not `//` (`login-form.tsx:64-66`).

## 7. Capability Registry dependencies

- Intake capability: `project.intake` (`available`, `publicVisible`, route `/workspace/projects/new`)
- New resolver: `web/src/lib/landing/public-landing.ts`
- Public nav unchanged (3 items) — landing has separate PublicHeader

## 8. Existing commercial components reused

`CommercialButton`, `CommercialCard`, `CommercialTimeline`

## 9. Visual / UX defects (baseline)

- Large master logo dominated hero (workspace panel aesthetic)
- No sections for process, result, trust
- No public header/footer separation
- No EN landing copy on `/`
- Metadata generic (`PRODUCT_BRAND.displayName` only)

## 10. Files to change

| File | Action |
|------|--------|
| `web/src/components/brand/public/*` | Add public shell + sections |
| `web/src/components/brand/public-landing-view.tsx` | Wire new tree |
| `web/src/lib/landing/*` | Registry CTA resolver + metadata |
| `web/src/lib/i18n/translations/{ru,en}.ts` | Landing copy |
| `web/src/app/page.tsx` | SEO metadata |
| `web/e2e/commercial-ux-slice-f-landing.spec.ts` | Browser suite |
| `web/scripts/run-commercial-ux-slice-f-gate.ps1` | Verification gate |

## 11. Tests

Unit: `public-landing.test.ts` (10 cases)  
E2E: scenarios A–Q per task brief  
Regression: capability registry + Slice E + A–D + 01F + 01G + BIV recovery

## 12. Risks

| Risk | Mitigation |
|------|------------|
| Landing promises planned modules | Registry-filtered CTAs; no reserved cards |
| AppShell leakage | Explicit PublicPageShell; E2E asserts no sidebar |
| CTA drift from registry | Unit + E2E assert registry resolver |
| Research auto-start | E2E intercept POST /runs on landing visit |

## 13. Owner decision required

**NO** — headline and positioning match approved task brief and existing `PRODUCT_BRAND.hero` meaning.
