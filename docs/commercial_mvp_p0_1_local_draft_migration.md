# Commercial MVP P0.1 — Local draft migration

## Rules

- localStorage drafts are **never deleted** by P0.1
- **No auto-upload** on page load
- Mock mode: full brief stays local
- Backend/hybrid: explicit CTA **«Сохранить полный бриф в Marketsynth»**

## Flow

1. Ensure Project core exists (I2 sync)
2. Validate / show readiness
3. Map draft → ProjectBrief body
4. Show field-loss (FE-only / no file content)
5. User confirms
6. Create or update draft brief
7. Optional submit
8. Store `briefSync` meta on local draft
9. Investigate handoff may reference brief version — **no Investigation entity created**

## Conflicts

`reconcileBriefFingerprints` returns options: keep local / load backend / create new version / cancel — **never silent merge**.
