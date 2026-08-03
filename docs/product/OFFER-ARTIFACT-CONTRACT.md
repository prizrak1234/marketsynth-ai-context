# Offer Artifact Contract (PRODUCT-01)

Persisted commercial Offer produced by `ms.skill.offer_builder` runtime adapter.

## Tables

- `offer_artifacts` — logical artifact, approval status, skill lineage
- `offer_artifact_versions` — immutable versions with `output_json` + hashes
- `offer_review_events` — human approve/reject/revision audit
- `commercial_upstream_snapshots` — MV/positioning/claims/CIM snapshots per Launch Pack

## Version rules

- Approved version is immutable.
- Revision creates new `version_number` with `revision_of_id`.
- Approval requires matching `expected_output_hash`.
- Only one current review candidate per Launch Pack.

## Customer-visible fields (`OfferArtifactDetail`)

| Field | Description |
|-------|-------------|
| offer_title / offer_summary | Headline + promise |
| problem_statement | Core customer problem |
| promised_outcome | Desired outcome |
| value_proposition | Positioning-linked value |
| offer_components | Product/service components |
| proof_references | Substantiated proof elements |
| conditions | Inherited MV conditions |
| unsupported_claims / evidence_gaps | Honest limits |
| cta | Call to action |
| human_review_required | Always true until owner approves |

Internal fields (skill_id, package_hash) exist in API for lineage but are not shown in customer UI.
