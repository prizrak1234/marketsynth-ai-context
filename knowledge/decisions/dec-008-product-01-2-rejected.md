# DEC-008: PRODUCT-01.2 Rejected

**Date:** 2026-07-24  
**Status:** Rejected with findings

## Context

Owner click-through on `/workspace` revealed commercial honesty failures in BIV path.

## Decision

PRODUCT-01.2 **rejected_with_findings**. Open **PRODUCT-01.3** as P0 integrity repair before any PRODUCT-01 freeze or PRODUCT-MEDIA-01.

## Observed failures

- Generic prefilled idea analyzed without confirmation
- «Подтверждённые выводы» with boilerplate/scraped content
- Verdict with 87% confidence without substantiation
- Stages green without readable outputs

## Consequences

- Offer Builder out of scope for 01.3 except regression
- Blocks PRODUCT-00.5 audit
- Launch Pack skill gaps remain secondary to integrity

## Verification

[docs/product/PRODUCT-01.3-BIV-INTAKE-EVIDENCE-REPORT-INTEGRITY.md](../../docs/product/PRODUCT-01.3-BIV-INTAKE-EVIDENCE-REPORT-INTEGRITY.md)
