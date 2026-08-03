# Reference image domain (H2.6A-R)

Owner-scoped uploaded visuals used as generation references.

## Entities

- `ReferenceVisualAsset` — one uploaded file (max 15 per set).
- `ReferenceSet` — durable container with preservation profile and consent flag.

## Limits (server-enforced)

See `REFERENCE_IMAGE_*` in config / `.env.example`.

## Honesty

Generative preservation maximizes recognizability. It does **not** guarantee
100% identity. Exact logos should prefer deterministic compositing.
