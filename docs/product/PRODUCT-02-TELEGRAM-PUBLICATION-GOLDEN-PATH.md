# PRODUCT-02 — Governed Content & Publication Golden Path

**Status:** `blocked` — after **PRODUCT-01 freeze** (steps A–F of [PRODUCT-FINISH-01](./PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md))  
**Channel:** Telegram only (v1)

---

## Golden path segment

```
Approved Offer
  → Telegram content brief
  → Telegram post draft
  → Human edit
  → Approve
  → Publish (native Telegram)
  → message_id
  → Evidence persisted
  → reload restores same publication record
```

---

## In scope

- One channel: **Telegram**
- Human approval before publish (no bypass)
- Real `message_id` after publish
- Evidence / audit trail
- Customer-safe errors

## Out of scope (v1)

- YouTube, LinkedIn, site, video
- Multi-channel strategy UI
- Higgsfield / image generation
- Presentation decks

---

## Exit criterion

Owner E2E: approved offer → edited post → live Telegram message → reload shows same state.

Parent: [PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md](./PRODUCT-FINISH-01-COMMERCIAL-GOLDEN-PATH.md)
