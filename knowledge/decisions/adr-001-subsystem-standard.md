# ADR-001: Marketsynth Subsystem Standard

**Date:** 2026  
**Status:** Accepted  
**Canonical doc:** [docs/architecture/adr_subsystem_standard.md](../../docs/architecture/adr_subsystem_standard.md)

## Context

Substantial product capabilities were implemented as services/APIs without unified lifecycle, operator, manifest, or honest readiness reporting.

## Decision

All substantial capabilities MUST follow the **Marketsynth Subsystem Standard**: lifecycle states, operator runbook, immutable manifest, recipes, preflight, paid approval where applicable, and honest capability reporting.

## Alternatives considered

- Ad-hoc per-feature architecture — rejected (drift, duplicate runtimes)
- Full microservices split — rejected (premature for current scale)

## Consequences

- New modules evaluated against compliance matrix before acceptance
- `tests/test_architecture_subsystem_standard.py` as invariant
- Identity, Video, BIV map to this standard
- Working service/API alone is NOT complete subsystem

## Verification

`uv run pytest tests/test_architecture_subsystem_standard.py -q`
