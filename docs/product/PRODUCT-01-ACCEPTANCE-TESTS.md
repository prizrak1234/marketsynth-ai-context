# PRODUCT-01 Acceptance Tests

## Automated

```bash
uv run pytest tests/test_product_01_offer_builder_cwf.py -q
uv run pytest tests/test_cwf_1a_launch_pack_decision.py tests/test_skill_02_8_offer_builder.py -q
cd web && npm run typecheck
```

## Owner click-through

1. Open `/workspace`, run BIV on a proceed-eligible idea.
2. Click **Подготовить запуск**.
3. Confirm Offer card appears (not generic assistant).
4. Review sections: problem, outcome, value, proof, conditions, CTA.
5. **Утвердить оффер** → badge shows approved; Launch Pack workflow `offer_approved`.
6. Reload page → Offer state restores from backend.
7. Optional: request revision → new version number visible in history toggle.

## Explicit exclusions verified

- No Telegram posts generated
- No Higgsfield / visuals
- No Content Strategy UI
- Frozen offer_builder hash unchanged (`test_01_frozen_offer_builder_package_hash_unchanged`)
