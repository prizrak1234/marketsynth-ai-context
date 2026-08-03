# P1.3 Frontend Integration Audit

## Routes (frozen A1–A6)

`/`, `/workspace`, intake wizard, investigation, verdict, strategy, pivot, implementation.

## Guards

Client-side eligibility checks exist; **server APIs remain authoritative**. No Next middleware added in P1.3.

## Integration modes

| Mode | Behavior |
|------|----------|
| MOCK | Demo only; handoff write blocked |
| BACKEND | Real data; no mock success on error |
| HYBRID | Backend authoritative; local previews labelled |

## Adapter patch

I6 messages updated: local preview non-writing; durable draft via P1.2 preview/confirm adapters.

## Limitation

Direct URL access may show shell UI; domain writes still fail server-side without eligibility.
