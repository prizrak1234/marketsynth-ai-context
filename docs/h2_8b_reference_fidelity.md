# H2.8B — Reference Fidelity Hardening

Status: **implemented in code; identity Product Gate not owner-accepted**.

Follow-up: [H2.8C — Reference Composer](h2_8c_reference_composer.md) (clarification trap + preservation controls).

## Goals

1. Replace raw `duplicate_checksum` UX with idempotent reference reuse.
2. Strengthen identity-preservation instructions and reference selection metadata.
3. Require owner visual review before treating a reference-guided result as accepted.
4. Do not claim 100% identity preservation.

## 1. duplicate_checksum root cause

Upload computed SHA-256 after normalize/re-encode. Same-owner duplicate raised `ReferenceUploadError("duplicate_checksum")` → HTTP 400 envelope with `error_code=duplicate_checksum`. Frontend preferred `error_code` over `safe_message`, so the raw code appeared in Home UI.

## 2. Idempotent reuse behavior

Same owner + same checksum:

| Case | Behavior | `attach_status` | Message |
|------|----------|-----------------|---------|
| Already in current ReferenceSet | No second storage; return existing asset | `already_attached` | «Этот референс уже добавлен.» |
| Exists for owner in another set | Link existing asset into set | `reused_existing_asset` | «Файл уже был загружен и использован повторно.» |
| Same bytes, other owner | Opaque create for that owner (no cross-owner leak) | `created` | — |

Raw `duplicate_checksum` is not returned on the happy path.

## 3. UI localization

- Upload client prefers `safe_message`.
- `errors.duplicate_checksum` / `reference_binding_failure` / `semantic_mismatch` / `low_identity_consistency` mapped in i18n.
- Attach info shown as non-error notice (`home-reference-info`).

## 4–8. ReferenceSet / profile / mode

- Selection summary: `Использовано N из M` + tip when person set has &lt;3 refs.
- `IdentityPreservationProfile` in contracts + `app/domain/identity_preservation.py`.
- Provider prompt built as sections: SUBJECT IDENTITY / ALLOWED / FORBIDDEN / REFERENCE PRIORITY / SCENE.
- With references: strongest path = `images.edit` (requested/actual `reference_guided_generation`); **no silent text_to_image fallback**.
- Metadata: primary id, selected/excluded ids, profile version, `input_fidelity`, parent_asset_id, strengthen flag.

## 9–10. Review gate + strengthen

- Reference-guided assets start as `awaiting_identity_review` (not auto-«Готово»).
- Heuristic consistency assist only (`high|medium|low|unavailable`) — never biometric wording.
- Low consistency → recommend strengthen / regenerate.
- «Усилить сходство» passes `strengthen_likeness=true` + `parent_asset_id`; previous asset remains immutable.

## 11. Exact brand vs person

Unchanged: logo/exact product prefers deterministic source file; person mode is generative preservation + owner review.

## Manual acceptance (owner)

Do **not** mark the identity Product Gate accepted until the owner confirms recognizable similarity in a real browser with 4–6 authorized adult photos (front / three-quarter / profile / half-body).

Suggested prompt remains in the H2.8B brief.

## Tests

- `tests/test_phase_h2_6a_r_reference_images.py` — duplicate → `already_attached`
- `tests/test_phase_h2_8b_reference_fidelity.py` — reuse, isolation, profile sections, review gate, no campaign/publish markers

## Confirmations

- No new product skills started (no H2.9).
- No remote Git operations performed for this phase.
- Home layout not redesigned.
