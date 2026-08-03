# BIV Analysis Context Contract

**Slice:** PRODUCT-01.3A  
**Binding rule:** No confirmed analysis context → no BIV run → no verdict → no Offer.

---

## States

| State | Analysis allowed |
|-------|------------------|
| `empty` | No |
| `draft_entered` | No |
| `hydrated_unconfirmed` | No |
| `editing` | No |
| `confirmed` | Yes |
| `analysis_requested` | In flight |
| `analyzing` | In flight |
| `completed` | Re-display only (same hash) |
| `blocked` | No |

---

## Record fields

Required on confirm:

- `idea_description`
- `product_or_service` (or derivable from idea)
- `target_customer` or explicit unknown
- `geography` or explicit unknown
- `analysis_goal`
- `input_snapshot_hash`
- `confirmed_by_user=true`
- `confirmed_at`

Optional: business model, pricing, stage, budget, competitors.

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/projects/{id}/analysis-contexts` | Create/update draft |
| GET | `/projects/{id}/analysis-contexts/current` | Current state (+ lazy hydrate) |
| POST | `/projects/{id}/analysis-contexts/{ctx}/confirm` | Confirm snapshot |
| POST | `/projects/{id}/analysis-contexts/{ctx}/edit` | Invalidate + edit |
| POST | `/projects/{id}/analysis-contexts/start-new` | New project + empty context |

BIV run body **must** include:

```json
{
  "analysis_context_id": "uuid",
  "input_snapshot_hash": "sha256-hex",
  "idempotency_key": "..."
}
```

---

## Error codes

| Code | HTTP |
|------|------|
| `analysis_context_required` | 409 |
| `hydrated_context_confirmation_required` | 409 |
| `analysis_context_incomplete` | 400 |
| `analysis_context_stale` | 409 |
| `analysis_context_not_found` | 404 |
| `invalid_analysis_context_state` | 409 |

---

## Snapshot integrity

- Hash computed from canonical JSON of `AnalysisContextFields`
- BIV run stores `analysis_context_id` + `input_snapshot_hash`
- Edit after confirm creates new unconfirmed draft; running analysis keeps old snapshot
