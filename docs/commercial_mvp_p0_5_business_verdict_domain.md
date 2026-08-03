# Commercial MVP P0.5 — BusinessVerdict Domain

## Purpose

`BusinessVerdict` is the durable backend Source of Truth for commercial viability:

> Should this business project proceed in its current form, under stated conditions, based on the available Evidence?

## Not in scope

- Execution / publication / budget approval
- Auto Strategy creation
- Agent Runs, LLM verdict generation, provider calls
- Replacing Evidence or human review

## Chain

`Project → ProjectBrief → Investigation → Source → Evidence → BusinessVerdict`

## Separation

| Concept | Answers |
|---|---|
| Evidence Summary / readiness | Enough quality Evidence? |
| BusinessVerdict | Proceed? Under what conditions? |
| Verdict review/approval | Human confirms commercial decision |
| Execution approval | May we run external actions? |

Readiness never selects verdict type. GO is never inferred solely from positive Evidence count.

## Types

Exact: `GO` · `CONDITIONAL_GO` · `NO_GO` · `INSUFFICIENT_DATA`

## Lifecycle

`draft → under_review → approved | rejected` · `superseded` · `archived`  
Approved is immutable; new versions supersede explicitly.

## Evidence snapshot

Every verdict binds an immutable Evidence snapshot (exact IDs + versions + hash). Later Evidence mutations do not rewrite prior verdicts.

## Migration

Append-only: `20260614_0033` revises `20260614_0032`.

## Firewall

Approve verdict → `creates_strategy=false`, `creates_execution_approval=false`, `creates_publication_approval=false`, `creates_agent_run=false`.
