# DEC-010: BotFazer Legacy Label Retained

**Date:** 2026-07  
**Status:** Active

## Context

Product rebranded to Marketsynth externally; codebase still uses BotFazer paths and labels.

## Decision

**Marketsynth** = product name. **BotFazer** = legacy package label — do NOT globally rename internals without explicit migration phase.

## Alternatives considered

- Big-bang rename — rejected (risk, no migration phase approved)

## Consequences

- Workspace path may show botfazer
- docs and SoT use both names with mapping
- AGENTS.md states rule clearly

## Verification

No mass rename PRs without migration phase doc
