# DEC-009: Explicit Execution Only

**Date:** 2026  
**Status:** Accepted

## Context

Auto-running skills, tools, publishing, or background workers creates commercial and safety risk.

## Decision

- Skills run one at a time, explicitly via API or Action Center
- No background workers for campaign/skill progression
- Publishing requires approved package + human approval for real send
- Paid media/video requires explicit_confirmation
- Scheduler = explicit due scan + dispatch only

## Alternatives considered

- n8n/Make as runtime — rejected for default path
- Auto wizard progression — rejected

## Consequences

- Documented across Operating Model, AGENTS.md, workflows
- Dry-run must never present as real publish

## Verification

Phase regression tests for action center, publishing, wizard
