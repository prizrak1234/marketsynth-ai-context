# Risk Findings — Archive Methodology

**Program:** ARCHIVE-MKT-01.0

---

## Critical (blocks customer-facing use without substantiation)

### R-01 — Financial outcome promises

**Source:** File 2 (crypto example), File 3–4 (earning potential)  
**Finding:** Promises of additional income (+10–20%, +30–100%) without verified representative evidence.  
**Control:** `claim_type: income_or_financial` → `human_review_required` + `legal_review_required`; default `prohibited` in fixtures.

### R-02 — «100% safety» framing

**Source:** Files 1, 3, 4  
**Finding:** Safety presented as absolute rather than residual-risk with mechanisms.  
**Control:** `claim_type: safety` with «100%» pattern → `substantiation_status: prohibited` or `requires_review`.

### R-03 — Technology infallibility

**Source:** File 4 — «технология не может не сработать», «бронебойность»  
**Finding:** Mechanism confidence substituted for customer outcome proof.  
**Control:** Claim Substantiation flags `unsupported`; delivery_mechanism requires `failure_modes` + `limitations`.

### R-04 — Counter-argument as proof

**Source:** File 2 — counter-arguments without evidence refs  
**Finding:** Rebuttals treated as substantiation.  
**Control:** fear responses must separate `fact`, `proof_requirement`, `mitigation`; inference ≠ verified.

---

## High (requires review or structural correction)

### R-05 — Assumption as customer agreement

**Source:** File 1 — «100% согласится на сделку»  
**Control:** Interview output forbids invented answers; assumptions tagged `trace_type: assumption`.

### R-06 — Statistical claims without source

**Source:** File 4 — «задавить цифрами»  
**Control:** `claim_type: statistical` requires `evidence_references` + source date.

### R-07 — Testimonial as universal proof

**Source:** File 4 — segment experience demonstration  
**Control:** testimonial ≠ population evidence; `proof_type: testimonial` with scope limitation.

### R-08 — Guarantee conflated with result

**Source:** Files 3–4 — refund/success fee alongside outcome claims  
**Control:** `risk_reversal ≠ guaranteed result` invariant in shared schemas and tests.

---

## Medium (methodology adaptation)

### R-09 — Leading interview questions

**Source:** File 1 structure  
**Control:** `leading_risk` field on each question; bias_warnings in output.

### R-10 — Yes/No satisfaction without evidence

**Source:** File 2 table  
**Control:** `satisfaction_status` requires evidence refs for `supported`; partial remains partial.

### R-11 — Price justification without comparison basis

**Source:** File 4 — cheaper/faster/earn more  
**Control:** `price-justification` requires `comparison_basis` or `assumption` marker.

---

## Regulated domain flags

Archive worked example uses **crypto trading** — high-risk financial domain.

| Flag | Action |
|------|--------|
| `regulated_domain: financial_trading` | All income/safety claims default prohibited in fixtures |
| `jurisdiction_context` | Required on claims when present |
| Archive examples | Fictional fixtures only; never copy as verified facts |

---

## Mitigation architecture

```
Customer meaning → promise_candidate (unsupported by default)
        ↓
Claim substantiation (gate)
        ↓
Offer Builder (supported claims only)
        ↓
Copywriting (future, separate gate)
```

**Critical path:** Claim Substantiation is mandatory before Offer primary promise.

---

## 01.0 verdict

No frozen package modification required. Proceed to 01.1.
