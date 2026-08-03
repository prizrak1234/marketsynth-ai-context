# H2.8D — Identity Engine Audit & Provider Decision

Status: **implemented in code; Identity Product Gate NOT owner-accepted**.

## Baseline (owner-rejected)

| Field | Value |
|-------|-------|
| Asset ID | `87dcc024-4040-4320-b2d1-8074f879e989` |
| UserRequest ID | `fb254112-36f3-4cd0-a4b6-dfe542e4481e` |
| ReferenceSet | `5261bdfd-b0ef-4359-b11c-77f0abbe543a` (6 stored) |
| Primary | `ea6c2df5-e4ae-49e1-891c-b8da0a267001` |
| Provider / model | `openai_images` / `gpt-image-1` |
| Requested / actual mode (pre-fix) | `reference_guided_generation` |
| Owner decision | `rejected_insufficient_similarity` (immutable freeze) |
| Paid A/B policy | harness first; `IDENTITY_AB_HARNESS_ENABLED` + `owner_confirmed_paid_calls` |

## Root cause (pre-H2.8D)

1. UI/selection claimed N references used (up to 10), but OpenAI `images.edit` received **only the primary file**.
2. Metadata set `references_provider_received = len(used_refs)` — dishonest.
3. Purpose defaults / ranking treated many files as face-like; body/pose could pollute identity.
4. Mode was soft-labeled `reference_guided_generation`, not `person_identity_preservation`.
5. GPTunnel + refs silently text-generated.

## What H2.8D changes

| Area | Change |
|------|--------|
| Selection | Person identity: max **5** identity refs; groups identity / appearance / scene; body cannot be primary face |
| Summary copy | `Загружено / Для внешности / Для стиля / Не использовано` + role labels |
| Transmit lineage | Honest `transmitted_reference_ids` (primary only for OpenAI edit) + dims/checksums/MIME/roles/section hashes/`provider_request_id` when available |
| Mode | `person_identity_preservation` required for person+refs |
| Adapter | `IdentityImageProvider` + `OpenAIIdentityAdapter`; GPTunnel → `identity_mode_not_supported` |
| Prompt | IDENTITY / SCENE / STYLE / NEGATIVE sections |
| Quality gate | Low similarity → `rejected_by_quality_gate` (not «Изображение создано») |
| Review | `rejected_insufficient_similarity` freezes asset (immutable) |
| A/B | `POST /generated-visual-assets/identity-ab-harness` gated; child assets via `parent_asset_id` |
| Upload default | purpose `other` (not auto `face_front`) |

## Acceptance report fields

| Field | Status |
|-------|--------|
| Failed asset + rejection | `87dcc024-…` → `rejected_insufficient_similarity` |
| Exact transmitted refs/order/roles | Primary-only transmit; roles in `selection_roles` / selection API |
| Primary payload proof | `OpenAIIdentityAdapter` → `edit_with_reference(primary)` only |
| Why N were previously selected | Cap 10 + face-like defaults (pre-fix) |
| New grouping | identity / appearance / scene / other; ≤5 identity |
| A/B results | Harness ready; **no paid calls run** without owner flag+confirm |
| Provider capability | `unknown` until owner-reviewed A/B |
| Suitability | Not decided — do not mark `suitable_for_identity` without recognition |
| Mode | `person_identity_preservation` |
| New asset IDs | Only after gated A/B |
| Similarity assist | `low`/`medium`/`high`/`unavailable` — never biometric |
| Owner visual decision | Baseline rejected; Gate **NOT ACCEPTED** |
| Replacement recommendation | If correct 3–4 face refs + low style freedom still wrong person → `unsuitable_for_identity`, replace engine |
| Tests | `tests/test_phase_h2_8d_identity_engine.py` (+ H2.8B/C) |
| No new skills / no remote Git | Confirmed |

## Provider capability

Classification starts as **`unknown`** until owner-reviewed A/B.

If after correct 3–4 face refs + low style freedom the person is still unrecognizable:

→ `unsuitable_for_identity` — stop prompt tuning; replace identity engine.

## Tests

```bash
uv run pytest tests/test_phase_h2_8d_identity_engine.py tests/test_phase_h2_8b_reference_fidelity.py tests/test_phase_h2_8c_reference_composer.py -q
```

## Confirmations

- No new product skills / no H2.9.
- No Home redesign / no extra preserve checkboxes.
- No Campaign / Make / n8n / budget / publication.
- No remote Git.
- Identity Product Gate remains **NOT ACCEPTED** until owner recognizes the person.
