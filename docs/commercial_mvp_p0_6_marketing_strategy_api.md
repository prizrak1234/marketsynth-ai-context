# Commercial MVP P0.6 — MarketingStrategy API

- `POST /projects/{id}/marketing-strategies`
- `POST /projects/{id}/marketing-strategies/build-draft`
- `GET /projects/{id}/marketing-strategies` (+ filters)
- `GET .../latest` · `GET/{id}` · `PATCH/{id}`
- `POST .../submit-review|approve|reject|return-draft|supersede|archive`

Auth + owner isolation. Exact Verdict version required. No MarketingPlan side effects.
