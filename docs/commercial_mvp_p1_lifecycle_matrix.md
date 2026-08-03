# Commercial MVP P1 — Lifecycle Matrices

## ProjectBrief

| From \ To | draft | submitted | superseded | archived |
|-----------|-------|-----------|------------|----------|
| draft | — | submit | — | archive* |
| submitted | — | — | via supersede new draft | archive |
| superseded | — | — | — | archive |
| archived | — | — | — | — |

\*Confirm service allows archive from draft where implemented. Content updates only in `draft`.

Side effects: **none** downstream (no auto Investigation).

## Investigation

| Status | Mutable? | Notes |
|--------|----------|-------|
| draft | yes | create from submitted brief |
| ready | yes | |
| active | yes | start |
| blocked | yes | block/resume |
| under_review | limited | submit-review |
| completed | immutable | |
| cancelled | immutable | |
| superseded | immutable | |

No auto Source/Evidence/Verdict/Strategy.

## Evidence

| Status | Content patch | Notes |
|--------|---------------|-------|
| draft | yes | |
| under_review | no | |
| accepted | no (content) | assessment actions constrained |
| rejected | no | |
| superseded | no | |
| archived | no | |

No auto Verdict.

## BusinessVerdict

| Status | Content patch | Notes |
|--------|---------------|-------|
| draft | yes | |
| under_review | no | |
| approved | no | only supersede/archive |
| rejected | no | |
| superseded | no | |
| archived | no | |

Approve **≠** Strategy create. No execution.

## MarketingStrategy

| Status | Content patch | Notes |
|--------|---------------|-------|
| draft | yes | requires eligible Verdict |
| under_review | no | |
| approved | no | only supersede/archive |
| rejected | no | |
| superseded | no | |
| archived | no | |

Approve **≠** MarketingPlan / Campaign / Agent Run / execution approval.

## Transition policy

- Forbidden transitions raise `InvalidStateError` → HTTP 409.
- No automatic downstream domain creation on any transition.
- Audit metadata: reviewed_by / reviewed_at / approved_at where present.
