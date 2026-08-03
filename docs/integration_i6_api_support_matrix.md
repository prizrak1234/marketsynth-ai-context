# Integration I6 — API support matrix

## MarketingPlan

| Endpoint | Side effects | I6 safe? | Notes |
|----------|--------------|----------|-------|
| `GET /projects/{id}/marketing-plans` | none | **yes** | list related ops plans |
| `GET .../marketing-plans/{id}` | none | **yes** | detail |
| `GET .../versions` | none | **yes** | display |
| `POST .../approve` | status→approved | **deferred** | not called from ImplPlan UI |
| `POST .../archive` | archived | **deferred** | not called |
| Generic `POST .../marketing-plans` | create draft | **missing** | blocker for write handoff |
| Scenario / chat / wizard create | creates plan | **deferred** | orthogonal; not Alpha handoff |
| `POST .../execution-runs` | may start run | **forbidden in I6** | separate execution spine |

## Approvals / execution / publication

| Resource | I6 |
|----------|-----|
| MarketingPlan approve | document + boundary only |
| execution-approvals | reference only; no create |
| publication approvals | reference only |
| Control Center planning state | unchanged; no rewrite |

## FE clients reused

- `web/src/lib/api/endpoints/marketing-plans.ts` — list/get/versions (approve unused by I6 UI)
- I5 `marketing-plan-adapter.ts` — ops view + plan selection

No duplicate APIs added.
