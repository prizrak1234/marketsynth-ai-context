# Product Alpha A7 — Decision

## Options

| Opt | Meaning |
|-----|---------|
| A | Retire A7 — real execution surfaces already cover it |
| B | Redesign A7 as UI over V2.2 Verified Execution |
| C | Keep A7 as pre-execution package only |
| D | Defer A7 until backend execution package exists |

## Recommendation: **B** (with freeze = deferred activation)

**Choose B.** Current A7 local Execution Package is a useful UX prototype for packaging dry-run / gates, but it is **not** SoT and must **not** ship as live execution.

- Real backend already has MarketingPlan execution-runs, readiness, execution-approvals, publishing — different surface.
- V2.2 will redefine Intent→Verification→Evidence; A7 should become the **product UI** over that chain, not a parallel local engine.
- Until then: keep code parked; backend mode must not invent package success (**I7 patch applied**).

**Not A:** do not delete — value for future Verified Execution UX.  
**Not C alone:** “pre-execution only” risks being mistaken for authorized packaging toward real ops.  
**Compatible with D:** activation deferred until backend Verified Execution package / Intent model exists.

## Explicit

- Do **not** implement A7 in I7.
- Do **not** call provider / Agent Run from A7 page.
- Do **not** unfreeze A7 before V2.2 authorization (or explicit product decision).
