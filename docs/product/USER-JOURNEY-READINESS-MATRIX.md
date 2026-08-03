# User Journey Readiness Matrix

**Audit:** PRODUCT-00  
**Legend:** ✅ yes · ⚠️ partial · ❌ no · — not applicable

## Journey overview

| ID | Journey | UI entry | Route | Skill contract | Runtime | Approval | Artifact | Review/edit | Publish | Evidence | Recovery | Blocker |
|----|---------|----------|-------|----------------|---------|----------|----------|-------------|---------|----------|----------|---------|
| A | Проверить идею | ✅ | `/workspace` BIV | ⚠️ BIV skill (not ms.skill pkg) | ✅ | — | ✅ verdict | ✅ | — | ✅ | ✅ hydrate | MCP/config; owner UX gate |
| B | Исследовать рынок | ⚠️ card | `/workspace/assistant` | ✅ market_research pkg | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Generic assistant |
| C | Проанализировать конкурентов | ❌ | assistant / legacy intake | ✅ competitor_analysis | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | No CWF route |
| D | Определить ICP | ❌ | — | ✅ icp_segmentation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | No UI/runtime |
| E | Создать позиционирование | ⚠️ grow-business | `/workspace/assistant` | ✅ positioning | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Generic assistant |
| F | Создать оффер | ⚠️ via K | `/workspace` Launch Pack | ✅ **offer_builder** | ✅ | ✅ | ✅ Offer | ✅ | ❌ | ⚠️ bridge | ✅ | **Owner acceptance PRODUCT-01.2** |
| G | Telegram-пост | ✅ sub-intent | `/workspace/assistant` | ❌ (copywriting deferred) | ⚠️ generic UR | ❌ | ⚠️ draft | ⚠️ | ❌ UI blocked | ❌ | ❌ | No content factory path |
| H | YouTube-сценарий | ✅ sub-intent | `/workspace/assistant` | ❌ | ⚠️ generic UR | ❌ | ⚠️ draft | ⚠️ | — | ❌ | ❌ | Same as G |
| I | Контент-план | ✅ sub-intent | `/workspace/assistant` | ❌ content_strategy | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Deferred capability |
| J | Презентация | ❌ | — | ✅ presentation_architecture | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | No UI |
| K | Подготовить запуск | ✅ | `/workspace` Launch Pack | ⚠️ + offer_builder | ✅ | ✅ | ✅ Offer | ✅ | ❌ | ⚠️ | ✅ | **Owner acceptance PRODUCT-01.2** |
| L | Опубликовать после approval | ❌ customer | owner content-factory | ⚠️ pub packages | ✅ backend | ⚠️ API | ⚠️ | ⚠️ | ❌ UI dry-run | ⚠️ logs | ❌ | Review/channels empty |

---

## Commercial status per journey

| Journey | Status |
|---------|--------|
| A | **production_user_ready** (single governed path) |
| F | **integrated_but_unpolished** — runtime + review UI; owner gate PRODUCT-01.2 |
| K | **integrated_but_unpolished** — Offer delivery; owner gate PRODUCT-01.2 |
| C, D, I, J | **contract_only** or **deferred** |
| L | **runtime_ready_no_UI** (Telegram backend) |

---

## Intent catalog mapping

Source: `web/src/lib/home/user-intent-catalog.ts`, `intent-navigation.ts`

| User intent | Declared status | Actual backend |
|-------------|-----------------|----------------|
| validate-idea | supported | BIV ✅ |
| create-content → Telegram | supported | Generic user request ⚠️ |
| create-content → YouTube | supported | Generic user request ⚠️ |
| create-content → content plan | supported | Generic user request ⚠️ |
| market-research | partial | Generic assistant |
| grow-business | partial | Generic assistant |
| prepare-launch | partial | Assistant card + Launch Pack post-verdict (request only) |

---

## Golden path gap (owner expectation vs reality)

**Expected commercial chain:**

```
Intent → Context → Research → ICP → Validation → Positioning → Claims → Offer
→ Content Strategy → Copy → Approval → Publish → Evidence
```

**Actual customer path today:**

```
Intent → [BIV if idea] → Verdict → [Launch Pack request] → STOP
         OR
Intent → Generic Assistant → optional content draft → STOP
```

**Planned gate (architecture accepted, not built):**

```
Verdict (GO / CONDITIONAL_GO / PILOT_ONLY)
  → Strategy / Launch Pack
  → PRE-LAUNCH READINESS (NOT_READY blocks ads)
  → Campaign Plan → Campaign Mode Selection → Ad Format Selection → Approval → Execution
```

See [PRE-LAUNCH-READINESS-01-ARCHITECTURE.md](./PRE-LAUNCH-READINESS-01-ARCHITECTURE.md), [YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01-ARCHITECTURE.md](./YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01-ARCHITECTURE.md), and [YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md](./YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md).

---

## Recovery / hydration

| Path | Works |
|------|-------|
| BIV project hydration after verdict | ✅ |
| Launch Pack journey hydration on `/workspace` | ✅ (shows prior request status) |
| Content Factory owner preview | ⚠️ off-path (`?owner_preview=content_factory`) |
| `/workspace/recovery-preview/r3` | Redirects to `/workspace` (orphaned) |
