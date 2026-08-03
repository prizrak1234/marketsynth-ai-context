# Commercial MVP P0.3 — Provenance and reliability

## Provenance types

| Value | Meaning |
|-------|---------|
| official | Regulator / official company / government |
| primary | Direct interview, first-party analytics, original research |
| secondary | Media, market review, aggregator |
| user_provided | User-entered reference |
| uploaded | User-uploaded document metadata (no binary in P0.3) |
| internal | Internal company artifact |
| generated | Machine-generated / transformed — never high by default |
| unknown | Unspecified |

Provenance ≠ AI confidence ≠ Business Verdict.

## Reliability

`unverified` (default) \| `low` \| `medium` \| `high`

Identity is immutable. Reliability changes via `review-reliability` with audit entries in metadata (`reliability_reviews`). Generated provenance cannot be set to `high`.

## Freshness

`current` \| `acceptable` \| `outdated` \| `unknown`

May be explicit or derived from published/accessed/captured dates (90d / 365d rules). Invented only when dates exist; otherwise `unknown`.
