# Identity Provider Capability Matrix (H2.8E)

Do not claim capabilities not proven by a live owner-reviewed call.

| Provider | Supported mode claim | Refs accepted (API) | True supporting refs | Style ref | Identity strength | Cost | Verified date | Capability | Owner review |
|----------|---------------------|---------------------|----------------------|-----------|-------------------|------|---------------|------------|--------------|
| openai_images | person_identity_preservation (soft) | 1 primary via images.edit | **No** | No | No | paid_per_call | — | `unverified` / `unknown` | pending |
| gptunnel_images | text_to_image only | 0 for identity | No | No | No | paid_per_call | — | `unsuitable_for_identity` | n/a (fail-closed) |
| specialized_identity_reserved | person_identity_preservation | up to 5 (planned) | Planned | Planned | Planned | unknown | — | `unavailable` | not integrated |

## Baseline evidence (pre-qualification)

| Field | Value |
|-------|-------|
| Failed Asset | `87dcc024-4040-4320-b2d1-8074f879e989` |
| UserRequest | `fb254112-36f3-4cd0-a4b6-dfe542e4481e` |
| Owner decision | `rejected_insufficient_similarity` |
| Paid A/B executed | **0** |

## Update rule

After diagnostic call + owner review, update **Capability** and **Owner review** columns only. Never mark `suitable_for_identity` from unit tests.
