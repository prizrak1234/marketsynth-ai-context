# Offer Review Workflow (PRODUCT-01)

## States

| Offer status | Meaning |
|--------------|---------|
| review_required | Generated; awaiting owner |
| approved | Owner approved exact output_hash |
| rejected | Owner rejected |
| revision_requested | Prior version marked; new version generated |

## Actions

### Approve

`POST .../offers/{id}/approve` with `expected_output_hash`. Stale hash → 409 `stale_approval_hash`.

Launch Pack → `offer_approved`.

### Reject

`POST .../offers/{id}/reject`. Launch Pack → `offer_rejected`.

### Request revision

`POST .../offers/{id}/request-revision` with comment. Creates audit event + **new version** (v+1) in `review_required`.

## Rules

- Skill never sets approval.
- Rejected version cannot be approved without new version.
- Launch Pack does not complete in PRODUCT-01 — only advances through Offer gate.
