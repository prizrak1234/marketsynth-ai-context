# Controlled pilot scope (1–3 users)

## Allowed

- Create Project
- Complete ProjectBrief intake/submit
- Manual Investigation lifecycle
- Manual Source registration / attachment
- Manual Evidence create/accept/reject
- Deterministic BusinessVerdict draft → review → approve/reject
- MarketingStrategy draft → review → approve/reject
- ImplementationPlan draft → review → approve/reject
- Explicit MarketingPlan **draft** handoff (idempotent)
- Browser login / logout / session revoke
- Read commercial lineage in Workspace

## Not allowed

- Autonomous research / Agent Run orchestration
- Real Campaign launch or execution
- LLM/provider publishing or media generation (flags off)
- MarketingPlan approval → specialist dispatch
- Budget transactions / ad spend
- Public signup or open registration
- Product Alpha A7
- AI.592
- Architecture V2.2 Verified Execution
- Any change to legacy drifted `botfazer` database

## Mode requirements

- Frontend integration mode: `backend`
- No silent mock fallback for commercial path
- Handoff remains draft-only
