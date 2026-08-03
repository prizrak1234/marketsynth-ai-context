# DEC-005: DIS Deferred Until CGP.10C

**Date:** 2026  
**Status:** Accepted with UI decoupling condition

## Context

Digital Identity System architecture accepted but Home UX still ambiguous about deliverable selection.

## Decision

DIS implementation **FORBIDDEN** until:
1. CGP.10C deliverable-aware Home accepted
2. Narrow vertical identity slices complete

Home must choose **what to create** before identity work resumes.

## Alternatives considered

- Implement DIS immediately — rejected (UI coupling)
- Cancel DIS — rejected (architecture accepted with patches)

## Consequences

- H2.8E subsystem built but not commercial
- Identity Product Gate requires owner person recognition
- No Campaign/Make/publication from identity track

## Verification

[docs/phase_cgp_10c_deliverable_selection_ux.md](../../docs/phase_cgp_10c_deliverable_selection_ux.md)
