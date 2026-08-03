# Integration I4 — Local verdict reconciliation

Key: `marketsynth.product_alpha.verdict.v1.{projectId}`

| Mode | Behavior |
|------|----------|
| mock | Untouched Alpha scenarios |
| hybrid | Local preview shown with origin label; optional supervisor/CC as **input signals** |
| backend | No local substitution; empty + unsupported |

Rules:

- no automatic upload to backend;
- no silent overwrite;
- do not delete local versions in I4;
- when backend entity exists later, approved backend is authoritative after fingerprint compare + conflict UI.

Code: `localVerdictReconciliationPolicy()`, `canAutoUploadLocalVerdictToBackend() === false`.
