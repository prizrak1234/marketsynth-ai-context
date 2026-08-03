# DEC-004: VIDEO Track Frozen

**Date:** 2026-07-22  
**Status:** Accepted

## Context

Video expansion risked unbounded provider work before commercial pilot proved i2v path.

## Decision

**VIDEO = FROZEN** until Controlled Pilot completes.

Allowed: P0 bugfixes on accepted image→video path (VS.2A-P-R).

Forbidden: VS.2B, text-to-video, start/end frame, long-form, montage, identity video, new video providers.

## Alternatives considered

- Continue VS.2B in parallel — rejected
- Remove video entirely — rejected (VS.2A accepted value)

## Consequences

- Baseline tag `project-freeze-2026-07-22`
- Owner preview at `?owner_preview=video` only
- Paid smoke via explicit_confirmation

## Verification

VS.2A acceptance commit `691dccc`
