# ARCHIVE-MKT-01 — Integrated Freeze Audit

**Date:** 2026-07-23  
**Verdict:** **CONDITIONALLY READY**

## Scope

Archive-derived contour:

```
CIM → Customer Interview Design → Customer Meaning Extraction
  → Market Validation → Positioning → Claim Substantiation → Offer Builder
```

## Package hashes (candidate)

| Package | Version | Hash |
|---------|---------|------|
| `ms.skill.customer_interview_design` | 0.1.0 | `e9e3b3f213e04e8a455285bb2f6c7aaf6f9856ae2a8d9738e5970bd98a92e8f2` |
| `ms.skill.customer_meaning_extraction` | 0.1.0 | `acc0082a88d867f340e14ef9fc5a5590c57f3799b4f29016b97662c39f97d771` |
| `ms.skill.claim_substantiation` | 0.1.0 | `faad9e2f23e1cc318d3aefa56e4943188b8204751882af870420da70016583b4` |
| `ms.skill.offer_builder` | 0.1.0 | `b637c3920066953f3080c8dc3e7c58bc08dc95138a85c545cac04d80a04d02f4` |
| Marketing Claims bundle | 0.1.0 | `c29ca2c08ccbb8861206fcc855e966c93d50b68264d8d9bdd096e13cd5c32f8d` |

## Frozen upstream (unchanged)

| Package | Hash |
|---------|------|
| CIM bundle | `b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea` |
| Positioning 0.1.0 | `cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6` |
| Market Validation 0.2.0 | `ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a` |

## Invariants (30)

All enforced by `tests/test_archive_mkt_01_6_foundation_invariants.py` and package tests.

1. Archive source is methodology only.
2. Interview questions are not evidence.
3. Customer answers remain unverified until supported.
4. CIM remains canonical customer model.
5. Meaning Extraction cannot redefine segments.
6. Positioning cannot redefine CIM.
7. Claim Substantiation is mandatory before Offer claims.
8. Unsupported claim cannot reach preferred Offer.
9. Prohibited claim cannot reach downstream copy input.
10. Guaranteed income rejected.
11. «100% safety» rejected.
12. Guarantee does not prove result.
13. Testimonial is not universal proof (schema policy).
14. Price justification requires evidence or explicit assumption.
15. Market Validation verdict remains unchanged.
16. MV stop blocks preferred Offer.
17. MV defer allows exploratory work only.
18–19. Inherited blockers/conditions preserved.
20. Offer readiness ≠ approval.
21–23. No Skill executes; no tools/connectors; no persistence/API/UI/MCP.
24. No frozen package modified in place.
25. Archive-derived hashes deterministic.
26–28. Registry candidate; production_eligible false; audit ≠ activation.
29. Lineage preserves source versions/hashes.
30. Marketing Director cannot bypass policy gates (capability map).

## Conditions

- Packages remain **candidate / non-executable** — no runtime loader.
- Legal validity of guarantees **deferred**.
- Regulated-niche claims require human/legal review — **deferred** operational workflow.
- Owner visual acceptance not required (no product UI change).

## Regression

```bash
uv run pytest tests/test_archive_mkt_01_6_foundation_invariants.py tests/test_archive_mkt_01_1_marketing_claim_contracts.py -q
uv run pytest tests/test_archive_mkt_01_2_customer_interview_design.py tests/test_archive_mkt_01_3_customer_meaning_extraction.py tests/test_archive_mkt_01_4_claim_substantiation.py tests/test_skill_02_8_offer_builder.py -q
```
