# CPH.2 — Happy path (browser)

Spec: `web/e2e/commercial-happy-path.spec.ts`

## Steps (UI)

1. Landing `/` — Marketsynth hero + «Проверить мою идею»
2. Intake wizard — all sections with deterministic clinic values; unknown money modes; competitors unknown
3. «Создать проект и начать исследование» → Project ID
4. Return to review → «Сохранить и зафиксировать (submit)» ProjectBrief
5. Investigation — create + start (no Agent Run)
6. Two Sources (no URL fetch)
7. Two Evidence → submit review → accept
8. Verdict — build draft → submit → approve
9. Strategy — build → submit → approve
10. ImplementationPlan — build → **«Подготовить к handoff (снять локальные gates)»** → submit → approve (`ready_for_handoff`)
11. Handoff preview (`eligible=true`) → checkbox «Создать только черновик MarketingPlan» → confirm draft
12. Repeat confirm (idempotent)
13. Refresh implementation workspace

Note: prepare-handoff clears local budget/approval gates and open conditions on the **draft** plan (same as P1.3 freeze). It does not create MarketingPlan or enable execution.

## Assertions

- Backend mode (no mock success strings)
- Refresh preserves Investigation sources/evidence
- MarketingPlan status `draft` only
- Lineage JSON written under artifacts
- Soft firewall probes on `/agent-runs`

## Screenshots

`01-landing` … `11-final-refresh` in lineage artifact dir.
