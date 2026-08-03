# Product Alpha Freeze — UX Baseline v1.0

**Status:** FROZEN as of Integration Phase I7  
**Name:** Marketsynth Product Alpha UX Baseline v1.0  
**Scope:** A1–A6 (A7 remains paused / not part of freeze shipping path)

## Frozen surfaces

- Landing / home brand presentation
- Workspace
- Project Intake wizard
- Investigation Workspace
- Business Verdict Workspace
- Marketing Strategy Workspace
- Pivot / Rework (NO_GO)
- Implementation Plan Workspace
- Brand tokens (`brand-tokens.css`, `PRODUCT_BRAND`)
- Terminology (GO / CONDITIONAL_GO / NO_GO / INSUFFICIENT_DATA; Marketsynth product naming)
- Route structure under `/workspace/...`
- Visual hierarchy and approved UX principles (evidence / risks / conditions visibility)

## Allowed after freeze (without new product decision)

- Backend integration wiring
- Bug fixes
- Accessibility / performance fixes
- Real data states / empty / error honesty
- Governance state display
- Verified execution states (when authorized)

## Forbidden without explicit product decision

- Redesign of frozen surfaces
- Route restructuring of A1–A6 journey
- Changing verdict vocabulary
- Replacing Workspace with chat-first UI
- Renaming Marketsynth (product)
- Removing evidence / risk / condition visibility from UX
- Activating A7 as SoT execution surface

## Notes

Local labelled previews remain until P0 backend domains land. Freeze locks **UX**, not the temporary SoT locality of Verdict/Strategy/ImplPlan.
