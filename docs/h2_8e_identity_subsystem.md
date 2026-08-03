# H2.8E — Identity Generation Subsystem & Provider Qualification

Status: **subsystem implemented under Subsystem Standard (Slice 0); Identity Product Gate NOT owner-accepted; no paid diagnostic executed.**

## Subsystem Standard

This capability is designed against:

- [architecture/marketsynth_subsystem_standard.md](architecture/marketsynth_subsystem_standard.md)
- [architecture/adr_subsystem_standard.md](architecture/adr_subsystem_standard.md)
- [architecture/subsystem_compliance_matrix.md](architecture/subsystem_compliance_matrix.md)

### Mapping to the standard

| Standard element | H2.8E realization |
|------------------|-------------------|
| Registry | Identity Provider Registry (`app/identity_generation/registry.py`) |
| Admission | Identity Reference Admission (`admission.py`) |
| Manifest | `IdentityReferenceManifest` (PostgreSQL JSON SoT) |
| Operator | `IdentityQualificationOperator` |
| Readiness | Identity Generation Readiness + Home wiring |
| Approval | Paid A/B Call Approval (`approve-calls`) |
| Quality | Visual Consistency Assistance (non-biometric) |
| Review | Owner Identity Review |
| Recipes | creative / style / identity / exact logo / strengthen / qualification |
| Runbook | [identity_generation_operator_runbook.md](identity_generation_operator_runbook.md) |
| Lineage | UserRequest → Manifest → Qualification Run → Provider Call → Asset → Review → Capability Decision |

**Not introduced:** second Runtime, second Agent Registry, parallel Asset store, new product skill.

## Goal

Productize identity generation as a governed subsystem (manifest + registry + preflight + paid approval + operator + runbook), not more prompt/checkbox tuning.

## Baseline

| Field | Value |
|-------|-------|
| Asset | `87dcc024-4040-4320-b2d1-8074f879e989` |
| UserRequest | `fb254112-36f3-4cd0-a4b6-dfe542e4481e` |
| Gate | **NOT ACCEPTED** |
| Paid calls | 0 (harness/operator gated; owner confirmation required) |

## Delivered layers

1. Identity Provider Registry — `app/identity_generation/registry.py`
2. Reference admission — `admission.py`
3. Immutable manifest SoT — `manifest.py` + `identity_reference_manifests`
4. Selection policy — reuses H2.8D `reference_selection.py` (≤5)
5. Readiness / preflight — `preflight.py` + Home wiring
6. Paid execution approval — qualification run `approve-calls`
7. Qualification operator — `operator.py`
8. Review + capability decision — `capability.py` (owner-authoritative)
9. Runbook + recipes + matrix — docs below
10. Slice 0 Subsystem Standard — architecture docs + invariant test

## APIs

| Method | Path |
|--------|------|
| GET | `/identity-generation/providers` |
| GET | `/identity-generation/recipes` |
| POST | `/identity-generation/readiness` |
| POST | `/identity-generation/manifests` |
| GET | `/identity-generation/manifests/{id}` |
| POST | `/identity-generation/qualification-runs` |
| POST | `/identity-generation/qualification-runs/{id}/advance` |
| POST | `/identity-generation/qualification-runs/{id}/approve-calls` |
| POST | `/identity-generation/qualification-runs/{id}/owner-review` |
| POST | `/identity-generation/qualification-runs/{id}/cancel` |
| GET | `/generated-visual-assets/readiness` (extended) |

## Honesty

OpenAI adapter: `references_provider_received_count = 1`.  
Supporting refs: `selected_but_not_transmitted` / RU copy in UI.

## Docs

- [identity_generation_operator_runbook.md](identity_generation_operator_runbook.md)
- [identity_provider_capability_matrix.md](identity_provider_capability_matrix.md)
- [architecture/marketsynth_subsystem_standard.md](architecture/marketsynth_subsystem_standard.md)

## Tests

```bash
uv run pytest tests/test_phase_h2_8e_identity_subsystem.py tests/test_phase_h2_8d_identity_engine.py tests/test_architecture_subsystem_standard.py -q
```

## Final report checklist

1. Baseline Asset — `87dcc024-…` frozen rejected  
2. Identity Gate — **NOT ACCEPTED**  
3. Registry — openai / gptunnel / reserved  
4. Active provider capability — `unknown`/`unverified` until owner A/B  
5–12. Manifest/selection/transmit — via readiness + manifests APIs  
13. Readiness — Home calls GET readiness + POST identity readiness  
14. Paid approval — awaiting owner; 0 diagnostic calls executed by default  
15–20. Qualification — operator ready; classification after owner review only  
21. Replacement — recommended if diagnostic fails likeness on primary-only adapter  
22. Runbook/recipes/standard — yes  
23. Tests — H2.8E + architecture invariant  
24. No new skill / no second Runtime / no duplicate ReferenceSet domain  
25. No publication / Campaign / Make / n8n / ads write  
26. No remote Git  

## Owner next step

Slice 0 standard is persisted. Next: show readiness + manifest + primary-only limitation → owner approves **one** diagnostic call → review → classify. Do not spend on B/C/D until adapter can transmit them.
