# ADR-001 — AI Context Repository

Status: ACCEPTED
Date: 2026-06-28

## Context

Project knowledge accumulated in chat creates risk of context loss and architectural drift.

## Decision

Create `marketsynth-ai-context` as the official AI-facing Source of Truth.

## Consequences

Positive:

- Cursor receives curated context;
- chat history stops being authoritative;
- future AI agents can onboard quickly.

Negative:

- documentation requires maintenance;
- stale documents must be audited.

## Rule

Only foundational and implementation-relevant documents are transferred.
