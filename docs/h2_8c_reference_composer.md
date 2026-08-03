# H2.8C — Reference Composer & Generation UX

Status: **implemented in code; not owner-accepted until browser generate works**.

## 1. Exact reason generation did not start

Owner had 6 references attached, but Home was still bound to a prior
`UserRequest` with `status=needs_clarification` and generic assistant copy
«Запрос пока слишком общий…».

Submit used `clarifyUserRequest(pendingClarifyId)` when `looksLikeNewTask`
was false. Scene prompts without verbs like «сгенерируй изображение» did not
escape that path. Backend `route_user_request` also required image-action
verbs; `reference_set_id` in `skill_inputs` did not force `image_generation`.

Result: Continue ≠ ImageGenerationExecution.

## 2–3. Clarification / ReferenceSet linkage

- Stale clarify thread owned the form (placeholder «Ответьте на уточнение…»).
- ReferenceSet lived in client state and was passed as `skill_inputs`, but
  without image route the skill never attached / executed.
- Hydration restored *any* historical `needs_clarification` as pending —
  even after newer completed requests.

## 4–9. What H2.8C adds

| Item | Change |
|------|--------|
| Composer draft | `web/src/lib/home/image-generation-composer.ts` |
| Person preserve / allow | Multi-checkbox sections in ReferenceUploadPanel |
| Per-file purpose | PATCH `/reference-visual-assets/{id}` + per-thumb select |
| Primary | Existing mark-primary + readiness gate |
| Readiness panel | «Готово к генерации» / blocking reasons |
| Explicit action | «Сгенерировать изображение» → `createUserRequest(selected_scenario=image_generation)` |
| Routing | `has_reference_set` + `force_image_generation` / scenario force |
| Hydration | Only newest request may own clarification |

## Browser acceptance (owner)

Do **not** mark H2.8C accepted until:

6 refs → purposes → primary → traits → fidelity=maximum →
button «Сгенерировать изображение» → real result → awaiting review.

## Tests

`uv run pytest tests/test_phase_h2_8c_reference_composer.py tests/test_phase_h2_8b_reference_fidelity.py -q`

## Confirmations

- No new product skills / no H2.9.
- No Home hero redesign.
- No remote Git.
- H2.8B / H2.8C identity gate not owner-accepted.
