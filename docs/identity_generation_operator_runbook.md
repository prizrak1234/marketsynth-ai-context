# Identity Generation Operator Runbook (H2.8E)

Subsystem: `identity_generation`  
Path: existing `design.image_generation` (no new product skill)  
Standard: [architecture/marketsynth_subsystem_standard.md](architecture/marketsynth_subsystem_standard.md)

## Purpose

Govern person-identity image generation with:

- preflight gates;
- provider registry (no secrets);
- immutable reference manifest (SoT);
- paid-call approval;
- qualification operator;
- honest transmit counts;
- owner review → provider capability decision.

Identity Product Gate remains **NOT ACCEPTED** until owner recognizes the subject.

This runbook follows the Marketsynth Subsystem lifecycle: Discovery → Setup → Configuration → Verification → Readiness → Operation → Review → Maintenance → Deprecation.

## Preflight

Before `person_identity_preservation`:

1. Authenticated owner
2. Valid ReferenceSet owned by user
3. ≥1 accepted image
4. Consent
5. Primary face reference
6. Identity profile available
7. Sufficient prompt
8. Provider supports mode + credentials configured
9. Paid approval when running qualification calls

API: `POST /identity-generation/readiness`  
Also: `GET /generated-visual-assets/readiness` (Home wired)

## Configuration

| Flag | Default | Role |
|------|---------|------|
| `IMAGE_GENERATION_ENABLED` | false | Master switch |
| `IMAGE_GENERATION_PROVIDER` | mock | Active provider |
| `OPENAI_API_KEY` | — | Via Settings only |
| `REFERENCE_IDENTITY_MAX_IMAGES` | 5 | Selection cap |
| `IDENTITY_AB_HARNESS_ENABLED` | false | Legacy A/B harness |

## Provider registry

`GET /identity-generation/providers`

| Code | Identity support | Max transmitted | Capability start |
|------|------------------|-----------------|------------------|
| `openai_images` | primary-only via images.edit | 1 | `unverified` |
| `gptunnel_images` | fail-closed | 0 | `unsuitable_for_identity` |
| `specialized_identity_reserved` | slot | 5 | `unavailable` |

Credentials never leave Settings / Integration Registry.

## Reference admission

uploaded → inspected → accepted_for_reference → classified → selected_or_excluded → frozen_in_manifest

Non-biometric checks only (readable, resolution, blur/occlusion notes, duplicate checksum, angle).

## Manifest creation

`POST /identity-generation/manifests`

Immutable JSON in PostgreSQL (`identity_reference_manifests`).  
Hash covers selected/excluded IDs, checksums, transmit plan, policy version.

## Paid approval

Operator stages stop at `awaiting_paid_approval`.

Owner choices:

- `approve_one_diagnostic` (variant A only) — **recommended first**
- `approve_full_comparison` (only adapter-supported variants)
- `reject` / `cancel`

No provider calls on page load. No four paid calls without explicit approval.

For OpenAI primary-only adapter: B/C/D are `unsupported_by_adapter` — do not fake transmit.

## Running diagnostic call

1. Create qualification run with baseline Asset `87dcc024-…`
2. Advance to approval
3. Approve one diagnostic
4. Execute variant A through existing generation path (manual/product generate or harness)
5. Record result on run → `awaiting_owner_review`

## Full qualification

Only if adapter can transmit supporting refs **or** owner explicitly wants more primary-only attempts.

## Owner review

`POST .../owner-review` with `acceptable` | `partial` | `not_recognizable`

## Provider classification

| Status | When |
|--------|------|
| `unknown` | No owner-reviewed paid run |
| `conditionally_suitable` | Partial likeness or primary-only limits |
| `unsuitable_for_identity` | Correct payload + still another person / insufficient refs |
| `suitable_for_identity` | True multi-ref identity mode + owner recognition + stability |

**Unit tests must never mark suitable.**

Stop condition: primary+prompt+max fidelity+low style freedom → another person → replace provider (H2.9), do not prompt-tune forever.

## Retry / cancellation

- `POST .../advance` is idempotent while waiting
- `POST .../cancel` sets `cancelled`
- Failed preflight → `preflight_failed` (fix inputs, recreate or advance after fix)

## Troubleshooting

| Symptom | Check |
|---------|--------|
| “не поддерживает сохранение внешности” | Active provider = gptunnel / unsupported |
| Claims 5 refs received | Bug — expect `references_provider_received_count=1` for OpenAI |
| Home shows no provider | Call `/generated-visual-assets/readiness` |
| Generate blocked | Consent, primary, prompt length, credentials |

## Cost control

One diagnostic first. Do not approve B/C/D when unsupported.

## Privacy and retention

Owner-scoped refs; checksums only in logs/metadata; no image bytes in logs; no auth headers logged; ephemeral provider upload handles closed after call; no public publish in this phase.

## No-secret policy

Keys only in `app.core.config` / `.env`. Registry serializes `configured: bool` only.

## Rollback

Alembic down `20260719_0049`. Code path still works without qualification runs (H2.8D generate remains).

## Known limitations

- OpenAI adapter transmits **one** primary image.
- Supporting refs influence selection/manifest but are `selected_but_not_transmitted`.
- Identity Gate not accepted until owner recognition after real qualification.
