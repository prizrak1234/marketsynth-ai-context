# Integration I2 — Future ProjectBrief / ProjectIntake (documentation only)

**Not implemented in I2.** No models, tables, routes, or migrations.

## Why

`Project` only supports `name` / `description` / `config`. Storing the full Product Alpha questionnaire in unvalidated `config` would falsely claim persistence and block a proper Brief domain.

## Candidate domain: `ProjectIntake` (or `ProjectBrief`)

Suggested properties (structured, validated — not opaque JSON bag as final design):

| Area | Properties |
|------|------------|
| Scope | `id`, `owner_id`, `project_id` |
| Lifecycle | `status`: draft \| submitted \| archived |
| Versioning | `version`, `updated_at`, optimistic concurrency token |
| Sections | basics, product, market, audience, economics (typed DTOs) |
| Quality | `assumptions[]`, `missing_data[]`, `readiness` snapshot |
| Materials | attachment **references** only (object storage ids later) |
| Audit | created/updated by, history of submissions |
| Link | optional `submission_fingerprint` for idempotent submit |

## Relationship to existing entities

- Reuse **Project** as parent (one active intake draft per project, or versioned history).
- Campaign Brief intake (AI.206+) may map later — do not silently dual-write in I2–I3.
- Investigation / Verdict remain separate domains (I3+).

## Until then

Frontend owns full `ProductIntakeDraft` in localStorage (+ linked-by-project key) with `backendSync` metadata pointing at the real Project id.
