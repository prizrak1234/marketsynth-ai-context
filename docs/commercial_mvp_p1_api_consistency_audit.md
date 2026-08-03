# Commercial MVP P1 — API Consistency Audit

## Pattern (target)

Nested under `/projects/{project_id}/…` with owner via `require_project_owner`.

| Domain | List | Latest | Get | Create | Patch | Review actions | Supersede/Archive |
|--------|------|--------|-----|--------|-------|----------------|-------------------|
| Briefs | GET | GET `/latest` | GET `{id}` | POST | PATCH | POST submit | supersede |
| Investigations | GET | GET `/latest` | GET `{id}` | POST | PATCH (+ stages) | start/block/… | supersede |
| Sources | GET | — (versions endpoint) | GET `{id}` | POST | — (no content PATCH) | reliability | supersede/archive |
| Evidence | GET (+ summary) | — | GET `{id}` | POST under inv | PATCH | accept/reject/… | supersede |
| Verdicts | GET project | GET `/latest` | GET `{id}` | POST under inv / build-draft | PATCH | submit/approve/… | supersede |
| Strategies | GET | GET `/latest` | GET `{id}` | POST / build-draft | PATCH | submit/approve/… | supersede |

## Consistency notes (non-blocking)

1. **Sources** lack `/latest` — versions via `/{id}/versions` (acceptable).
2. **Evidence** is nested under investigation (correct for scoping).
3. **Verdict create** is nested under investigation; list/latest at project level (intentional dual mount).
4. Error shape: InvalidState → 409 with `safe_message` / detail; validation → 422.
5. Pagination/filter vary by domain (Evidence/Sources list limits); not a correctness defect for P1.

## Correctness risks patched?

None requiring cosmetic route renames. Ownership on nested routes is consistent.

## Idempotency / duplicates

Fingerprint-based conflicts for Brief submit / Source register (project-scoped). Documented in P0.* fingerprint docs.
