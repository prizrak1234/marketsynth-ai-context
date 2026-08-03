# Controlled Pilot Hardening CPH.2 — Browser End-to-End

**Phase:** CPH.2  
**Date:** 2026-07-15  
**Pilot DB:** `botfazer_cph1` @ Alembic `20260614_0036`  
**Legacy DB:** `botfazer` @ orphan `20260608_0033` — **not used**

## Checkpoint

- CPH.1 commit: `86a15f9` — `chore: establish PostgreSQL pilot baseline`
- Framework: **Playwright** (Chromium) under `web/e2e/`
- Mode: `NEXT_PUBLIC_MARKETSYNTH_INTEGRATION_MODE=backend`

## What was fixed to unlock UI journey

Backend-mode lifecycle buttons were missing for Evidence accept, Verdict/Strategy/ImplPlan build→submit→approve. Minimal wirings (no redesign) enable a real browser path. MarketingPlan handoff panel already existed.

**CPH.2 handoff readiness:** draft ImplementationPlan from CONDITIONAL_GO starts as `conditionally_ready` (pending local gates). UI action `impl-prepare-handoff` («Подготовить к handoff») PATCHes gates/conditions the same way as P1.3 freeze — still draft-only, then submit→approve→handoff. No MarketingPlan until explicit confirm.

## Framework decision

- **Playwright** + Chromium only (no second E2E framework).
- Auth: seeded pilot API user + localStorage `marketsynth.e2e.api_key.v1` (no production auth bypass).
- Happy path must go through UI controls; API used only for seed/auth/lineage/firewall probes.

## Commands

```powershell
# Point at pilot DB only
$env:DATABASE_URL="postgresql+asyncpg://botfazer:***@localhost:5432/botfazer_cph1"

# One-shot orchestrator (starts services if needed)
uv run powershell -File scripts/cph2_run_browser_e2e.ps1
# Headed:
uv run powershell -File scripts/cph2_run_browser_e2e.ps1 -Headed
```

Artifacts: `web/test-results/cph2-artifactsage/<runId>/`, Playwright HTML report `web/playwright-report/`.

## Related docs

- [Test environment](controlled_pilot_cph_2_test_environment.md)
- [Test data policy](controlled_pilot_cph_2_test_data_policy.md)
- [Happy path](controlled_pilot_cph_2_happy_path.md)
- [Routing & errors](controlled_pilot_cph_2_routing_and_error_cases.md)
- [Execution firewall](controlled_pilot_cph_2_execution_firewall.md)
- [CI readiness](controlled_pilot_cph_2_ci_readiness.md)

## Roadmap

| Status | Track |
|--------|--------|
| Completed | Commercial MVP Backend Baseline v1.0 · CPH.1 · **CPH.2 Browser E2E** |
| **Current** | CPH.3 Auth and Session Hardening |
| Next | CPH.4 Backup/Restore · CPH.5 Observability → Pilot Readiness Gate |
| Paused | A7 · AI.592 · V2.2 |
