# PRODUCT-01.4 Slice E — Pre-Implementation Audit

> **Task:** PRODUCT-01.4-COMMERCIAL-UX-UNIFICATION-01E  
> **Date:** 2026-07-31  
> **Owner decision required:** NO (presentation-only unification)

## 1. Current component map

| Surface | Route | Component | Commercial replacement |
|---------|-------|-----------|------------------------|
| Wizard shell | `/workspace/projects/new/*` | `IntakeWizardShell` | `CommercialPageHeader`, `CommercialCard`, `CommercialButton`, `CommercialAlert`, `CommercialLoadingState` |
| Steps 1–7 | per-step routes | `Step*Form` | `IntakeStepFrame` + `FieldGroup` / `OptionalSection` |
| Fields | shared | `intake-fields.tsx` | Unified required/optional markers, focus rings |
| Review | `/review` | `StepReviewForm` | `CommercialCardInset`, `CommercialStatus`, `CommercialButton`, `CommercialAlert` |
| Diagnostics | review only | `IntakeDeveloperDiagnostics` | Unchanged; dev-mode gate preserved |

## 2. Persistence lifecycle

- Draft: `localStorage` key `marketsynth.product_alpha.intake_draft.v1`
- Autosave: `IntakeDraftProvider` debounced save + customer status indicator
- Backend: unchanged — project/brief sync only on golden-path submit

## 3. Submit lifecycle

Unchanged: `executeIntakeBriefGoldenPath` → sync project → brief → analysis context → confirm → user request → async POST `/runs`.

## 4. Canonical component mapping

See table §1. New primitives: `commercial/form/*`, `intake-wizard-copy.ts`, `useIntakeWizardCopy`.

## 5. UX defects (pre-fix)

- Hardcoded RU strings per step
- Inconsistent optional labels («необязательно», «Unknown»)
- Wizard shell not using commercial components
- Review gradient card vs canonical CardInset
- Competitors fields visible when «неизвестны» selected
- No customer autosave indicator
- P2: missing focus ring on `CommercialButton`, progressbar semantics

## 6. Scope / out of scope

**In:** presentation, i18n copy module, conditional competitors UI, a11y P2 on shared components.  
**Out:** questions, step order, validation rules, routes, backend, submit orchestration, Landing/Settings.

## 7. Files touched

`intake-wizard-shell.tsx`, `intake-fields.tsx`, `intake-draft-context.tsx`, all `step-*-form.tsx`, `commercial/form/*`, `commercial-button.tsx`, `commercial-progress.tsx`, E2E harness.

## 8. Tests

Unit: `intake-wizard-ux.test.ts` (+5). E2E: `commercial-ux-slice-e-verification.spec.ts`. Regressions: existing intake golden path + RUNTIME-01F unchanged contract.

## 9. Risks

- E2E requires auth + prod build for PASS evidence
- Partial i18n (wizard copy module, not full `ru.ts` tree migration)

## 10. Owner decision

**NO** — no question/order/API changes proposed.
