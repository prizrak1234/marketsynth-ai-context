# Runtime Invariants

Status: FROZEN

## Invariant 1 — Source of Truth Technology Independence

Source of Truth defines architecture semantics and data contracts.

Changing storage technology does not change SoT logic.

## Invariant 2 — Snapshot Lineage Completeness

Runtime objects must preserve lineage:

Context → Decision → Approval → Execution → Evidence → Outcome → Knowledge Candidate.

Missing lineage breaks auditability.

## Invariant 3 — Human Approval Before Real Execution

Real execution requires explicit approval.

Readiness is not approval.

## Invariant 4 — Tenant Boundary Completeness

Knowledge Candidate never crosses tenant boundary.

Runtime evidence, memory, snapshots and execution traces are tenant-scoped.

## Invariant 5 — COO Runtime Authority Limit

COO Runtime routes, schedules, assigns and escalates.

It does not determine business truth.

## Invariant 6 — Owner Unavailable Policy

If a required owner is unavailable, runtime must escalate according to policy instead of inventing approval.

## Invariant 7 — No Silent Architecture Mutation

Implementation may not change constitutional or architectural meaning without ADR/RFC update.
