# CPH.3 — Owner isolation matrix

Policy: **404** (non-disclosure) when `owner_id != current_user.id`.

| Domain | Cross-owner denied |
|--------|-------------------|
| Project | GET/PATCH |
| ProjectBrief | list/get |
| Investigation | list/get |
| Source | list |
| Evidence | via investigation routes |
| BusinessVerdict | list |
| MarketingStrategy | list |
| ImplementationPlan | get + handoff |
| MarketingPlan | list |

Verified by `tests/test_controlled_pilot_cph_3_owner_isolation.py` and browser isolation in `web/e2e/auth.spec.ts`.
