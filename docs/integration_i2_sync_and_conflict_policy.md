# Integration I2 — Sync and conflict policy

Frontend integration states on `ProjectIntakeDraft.backendSync` (not backend Project statuses):

| State | Meaning |
|-------|---------|
| `local_only` | No backend Project linked |
| `creating` | POST in flight |
| `update_pending` | PATCH in flight |
| `partially_synced` | Core on backend; full brief local (success) |
| `synced` | Reserved / treated like success for CTA |
| `conflict` | Ambiguous create or ownership/not-found without auto-create |
| `failed` | Known API/network failure after safe handling |

## Duplicate prevention

1. In-memory lock per `draft.id` while request active.
2. Submit button disabled while busy.
3. If `backendProjectId` set → **PATCH only** (never second POST for same draft).
4. Same submission fingerprint + already linked → navigate without new write.
5. Backend has **no** idempotency-key on `POST /projects` — do not invent one.

## Ambiguous create (network after possible server success)

1. Do **not** auto-retry POST.
2. Mark `conflict` + `ambiguous_create_result`.
3. Optional reconcile: `GET /projects` and match `config.marketsynth_i2.localDraftId`.
4. User action: “Сверить с Workspace” / open Workspace manually.

## Errors → UI actions

| Kind | Action |
|------|--------|
| `validation_error` | Fix name/description |
| `unauthorized` | Re-auth / set API key |
| `forbidden` | Return to Workspace |
| `project_not_found` | Reconcile; do not auto-create duplicate |
| `ambiguous_create_result` | Reconcile only |
| `network_error` / `backend_unavailable` | Preserve draft; retry later |
| Backend mode failure | **Never** convert to successful mock project create |

## Workspace

After success, navigate with real id; Workspace reload uses `loadWorkspaceProjects()`.  
Do not inject a second mock card for the same linked draft; backend card is SoT when linked.
