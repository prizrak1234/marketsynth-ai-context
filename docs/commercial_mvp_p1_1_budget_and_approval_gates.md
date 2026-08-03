# Commercial MVP P1.1 — Budget and Approval Gates

## Budget plan / gates

Planned structure only. Gate statuses use `approved_local` / `pending` — **not** financial authorization.  
`budget_gates_authorize_spend=false` on every API response.

## Approval gates

Local ImplementationPlan governance (`implementation_plan_review`, validation, offer, budget, …).  
**Not** backend generic execution/publication approvals.  
`approval_gates_are_local_only=true`.
