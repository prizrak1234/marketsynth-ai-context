# DEC-006: No LangGraph Marketing Default

**Date:** 2026  
**Status:** Accepted

## Context

Temptation to add agent orchestration frameworks for marketing conveyor.

## Decision

Do NOT add LangGraph, agent executors, or marketing pipelines unless owner explicitly requests phase 3+.

Marketing progression via explicit API calls, Action Center, wizard advance — not graph orchestration.

## Alternatives considered

- LangGraph for parallel specialists — rejected (frozen phases explicit)
- Auto ContentAsset from chat — rejected

## Consequences

- AGENTS.md and botfazer-foundation.mdc enforce rule
- Parallel specialist execution blocked by design

## Verification

Code review + AGENTS.md invariant
