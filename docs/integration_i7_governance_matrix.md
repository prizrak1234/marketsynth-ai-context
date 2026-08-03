# Integration I7 — Governance matrix

See also: `web/src/lib/integration/approval-boundary.ts`, `decision-semantics.ts`.

| Category | Authority | Persistence | Side effect | Authorizes external action? |
|----------|-----------|-------------|-------------|------------------------------|
| Product Alpha local review (generic UI) | Human / local | localStorage statuses | labelling only | **no** |
| Verdict local review | commercial preview | local | unlocks Strategy eligibility (local) | **no** |
| Strategy local review | GTM preview | local | unlocks Implementation eligibility (local) | **no** |
| Implementation Plan local review | delivery structure | local | unlocks handoff **preview** only | **no** |
| MarketingPlan approval | backend owner | MarketingPlan status | plan approved; **not** Agent Run | **no** (external) |
| Specialist output approval | backend | artifacts | downstream content gating | limited |
| Content asset approval | backend | assets | publishing prerequisite | limited |
| Budget approval | future / local gates | local (Alpha) / future | financial scope | **no** auto execution |
| Execution approval | backend gated | execution_approvals | real op authorization | **yes** (when flag on) |
| Publication approval | backend publishing | packages/jobs | publish path | **yes** (Telegram gated) |

## Rules

- No shared `approved: boolean` across categories without **discriminator**.
- Implementation Plan approval ≠ MarketingPlan approval ≠ execution approval ≠ publication approval.
- Business Verdict ≠ any of the above approvals.
