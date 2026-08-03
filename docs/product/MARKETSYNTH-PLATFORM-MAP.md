# Marketsynth Platform Map — Product Inventory & Positioning

**Status:** `owner_canonical_inventory` · **Implementation:** reference only — does not override active phase gates  
**Purpose:** preserve the full planned product surface so nothing is lost during narrow commercial slices  
**How it connects:** [MARKETSYNTH-OPERATING-MODEL.md](../MARKETSYNTH-OPERATING-MODEL.md) — canonical runtime, lifecycle, shared services  
**Legacy package label:** BotFazer (internals unchanged until explicit migration)

---

## Positioning (2026-07)

### Evolved definition

> **Marketsynth — AI-платформа для создания, запуска и развития бизнеса.**

More precise:

> **Marketsynth — AI Business Operating System**, которая помогает предпринимателю пройти путь **от идеи до масштабирования**.

Marketing is **one subsystem**, not the whole product. The name *Marketsynth* no longer limits scope — it reflects synthesis of market intelligence and business operations.

### Strategic invariant (unchanged)

> **Сначала проверить и сохранить деньги клиента — потом помогать инвестировать в развитие.**

This aligns with:

- BIV / Research before spend  
- Pre-Launch Readiness before ads  
- Human Approval before execution  
- Evidence before verdict  

See also: [HOME_PRODUCT_RULE.md](../HOME_PRODUCT_RULE.md), [commercial-product-directive](../.cursor/rules/commercial-product-directive.mdc).

### What Marketsynth is not

- Not a chatbot (conversation = interface)  
- Not an agent builder for power users  
- Not Make/n8n clone (workflows = reference / checklist, not default runtime)  
- Not «ещё один LLM, который что-то написал»

---

## End-to-end business journey (target)

```
Идея
  → Проверка идеи (BIV)
  → Исследование + Evidence
  → Коммерческий вердикт
  → Маркетинговая стратегия
  → Сайт
  → Дизайн
  → Копирайтинг
  → Контент
  → Видео
  → AI-агенты / автоматизация
  → Реклама (Direct, Telegram, …)
  → Продажи
  → Оптимизация
  → Масштабирование
  → [долгосрочно] Business Intelligence
```

**Active commercial slice (CWF.1):** Idea → Research → Verdict → Launch Pack → Telegram — see [CWF-SKILL-INTEGRATION-GAPS.md](./CWF-SKILL-INTEGRATION-GAPS.md).  
Everything else on this chain is **planned, partial, or frozen** unless a phase doc says otherwise.

---

## Capability domains (12 + platform pillars)

Legend: **✅ accepted/partial** · **🔄 active P0** · **📐 architecture only** · **⏸ frozen** · **📋 planned**

### 1. AI Business Research (ядро)

| Capability | Status | Notes |
|------------|--------|-------|
| Проверка бизнес-идеи (BIV) | 🔄 | CMVP.1.1 accepted; HARDENING-02 Evidence Funnel = P0 |
| Анализ рынка, конкурентов, ЦА | 🔄 | Research engine; evidence funnel bottleneck measured |
| SWOT, PEST | 📋 | Frameworks in knowledge; product surfacing TBD |
| Анализ спроса | 🔄 | Wordstat/tools exist; campaign integration frozen |
| Unit-экономика, риски, финансовая оценка | 📋 | Partial in BIV / economics modules |
| Коммерческий вердикт | ✅ | GO / CONDITIONAL / PILOT / HOLD / NO_GO |

**Docs:** [REAL-RESEARCH-READINESS.md](./REAL-RESEARCH-READINESS.md), [EVIDENCE-FUNNEL-ARCHITECTURE.md](./EVIDENCE-FUNNEL-ARCHITECTURE.md)

---

### 2. Маркетинговая стратегия

| Capability | Status |
|------------|--------|
| Позиционирование, УТП | 🔄 Offer Builder / CWF integration |
| CJM, сегментация, воронки | 📋 Marketing department v2 frozen |
| Контент-стратегия, медиа-план | 📋 |
| План запуска (Launch Pack) | ✅ CWF.1 boundary |

---

### 3. Реклама

| Capability | Status | Doc |
|------------|--------|-----|
| Яндекс Директ (execution) | 📋 | After Campaign Architect chain |
| Google Ads | 📋 | Future |
| Telegram Ads | 📋 | Aligns with Telegram track |
| Campaign Planner / Plan | 📋 | Queue #3 post-HARDENING |
| Campaign Mode Selector | 📐 | [YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01](./YANDEX-DIRECT-CAMPAIGN-MODE-SELECTOR-01-ARCHITECTURE.md) |
| Ad Format Selector | 📐 | [YANDEX-DIRECT-AD-FORMAT-SELECTOR-01](./YANDEX-DIRECT-AD-FORMAT-SELECTOR-01-ARCHITECTURE.md) |
| Pre-Launch Readiness | 📐 | [PRE-LAUNCH-READINESS-01](./PRE-LAUNCH-READINESS-01-ARCHITECTURE.md) |
| AI-оптимизация кампаний | 📋 | Post-execution + BI contour |

**Campaign Architect chain (Direct):** Plan → Mode + Objective → Ad Format → Creative → Approval → Execution → Optimize

---

### 4. Контент

| Channel / output | Status |
|------------------|--------|
| Telegram | ✅ publication path (CWF.1); frozen phases AI.60–75 |
| YouTube, Дзен, VK, LinkedIn, блоги, email | 📋 |
| SEO, контент-план, автопубликация | 📋 |

---

### 5. Видео

| Capability | Status |
|------------|--------|
| Сценарии, сториборды, Shorts/Reels/TikTok/YouTube | 📋 |
| Рекламные ролики, AI Avatar, озвучка, субтитры | 📋 |
| Video до 300 сек | ⏸ | VS.2A accepted; **VIDEO FROZEN** until Controlled Pilot |

**Doc:** [VIDEO_STUDIO_PRODUCT.md](../VIDEO_STUDIO_PRODUCT.md)

---

### 6. Дизайн

Баннеры, рекламные креативы, логотипы, фирменный стиль, презентации, изображения, инфографика.

| Status | Notes |
|--------|-------|
| ⏸ / 📋 | Identity / DIS — architecture accepted; implementation gated post-CGP.10C |

---

### 7. Копирайтинг

Отдельный большой модуль: продающие тексты, лендинги, статьи, email, КП, сценарии, объявления, SEO.

| Status |
|--------|
| 📋 Partial via content assets / Launch Pack; dedicated module not opened |

---

### 8. Создание сайтов

**Full cycle** — not «нарисовать лендинг»:

Landing · корпоративный · интернет-магазин · Tilda · HTML · SEO · UX · UI · тексты · **публикация**

| Status |
|--------|
| 📋 Programmer / site domain planned; Pre-Launch audits **site readiness** first |

---

### 9. AI-разработка (Programmer Domain)

Telegram-боты · AI-боты · AI-агенты · Make · n8n · MCP · LangGraph · API · интеграции · автоматизация

| Status | Notes |
|--------|-------|
| 📋 | Workflow library pilot (n8n templates) = draft only; no auto-execution |
| Rule | No LangGraph marketing orchestration unless explicit phase |

---

### 10. Маркетплейсы

Wildberries · Ozon · Яндекс Маркет — карточки, SEO карточек, инфографика, баннеры

| Status |
|--------|
| 📋 Linked from Campaign Mode `marketplace_sales` objective |

---

### 11. Автоматизация бизнеса

CRM · Google · Telegram · API · Make · n8n · Webhooks · автоматические процессы

| Status |
|--------|
| 📋 Business automation layer; distinct from marketing conveyor |

---

### 12. AI-команда специалистов

**Сейчас (marketing department v2 baseline):** Маркетолог · Аналитик · Исследователь · Дизайнер · Копирайтер · Программист

**Запланировано:** HR · Юрист · Финансист · Бухгалтер · Sales · Customer Success · Product Manager · Project Manager

| Status |
|--------|
| ✅ 14 roles frozen (AI.119); expansion 📋 |

**Doc:** [phase_ai_119_marketing_department_v2_freeze.md](../phase_ai_119_marketing_department_v2_freeze.md)

---

## Platform pillars (cross-cutting)

### Knowledge Base

Company knowledge that:

- accumulates successful research  
- stores decisions  
- reuses patterns  
- improves subsequent runs  

| Status | Doc |
|--------|-----|
| 🔄 KG.1 / KG.2 | [knowledge_governance_subsystem.md](../knowledge_governance_subsystem.md), [KNOWLEDGE_IMPORT_PLAN.md](../KNOWLEDGE_IMPORT_PLAN.md) |

**Citation contract:** Answer + Evidence + Source + Confidence — non-negotiable.

---

### Workspace

Not chat — **operating surface:**

- projects · history · versions  
- research · reports · publications · files  

| Status |
|--------|
| ✅ `/workspace` hydration, BIV, Launch Pack journeys |

**Doc:** [workspace_home_usp.md](../workspace_home_usp.md)

---

### Human Approval

Critical path:

```
AI proposal → Human Approval → Execution
```

| Status |
|--------|
| ✅ Architecture strength; Telegram publish, paid smoke, campaign launch gated |

---

### Execution Layer

After Direct and peers mature — **full loop:**

```
исследовал → спланировал → создал → согласовал → запустил → проанализировал → оптимизировал
```

| Status |
|--------|
| 📋 Yandex Direct Execution = queue #6; optimization 📋 |

---

## Priority queue (advertising / research — current)

Does **not** reorder the 12 domains — only the **active engineering track**:

| # | Slice | Status |
|---|-------|--------|
| 1 | REAL-RESEARCH-HARDENING-02 (Evidence Funnel) | 🔄 P0 |
| 2 | PRE-LAUNCH-READINESS-01 | 📐 |
| 3 | Campaign Plan | 📋 |
| 4 | Campaign Mode Selector | 📐 |
| 5 | Ad Format Selector | 📐 |
| 6 | Yandex Direct Execution | 📋 |

Everything else in this map remains **documented intent** until unlocked by constitution / owner gate.

---

## Long-term strategic goal: Business Intelligence (BI)

**Not now.** Becomes relevant when the platform has:

- site + ads + CRM + analytics + sales data  

Marketsynth should then answer **operating questions**, not only create assets:

- Why did sales drop?  
- Why did CAC rise?  
- Which channels turned unprofitable?  
- Which ads stopped working?  
- Where are customers lost?  
- What to change to increase profit?  

BI = **manage business from data**, not only **produce marketing**.

| Status |
|--------|
| 📋 Strategic north star; no slice opened |

---

## How to use this document

| Audience | Use |
|----------|-----|
| Owner | Single inventory — nothing «forgotten» off-roadmap |
| Product / Cursor | Check new work against domain + active queue |
| Commercial slices | Must cite which domain they advance and which gate they respect |

**Rule:** Adding a row here does **not** authorize implementation. Phase docs + owner acceptance still required.

---

## Cross-references

- [MARKETSYNTH-OPERATING-MODEL.md](../MARKETSYNTH-OPERATING-MODEL.md) — **how modules work together** (CEO-level)
- [PROJECT_VISION.md](../PROJECT_VISION.md) — why Marketsynth exists  
- [AGENT_OS_ARCHITECTURE.md](../AGENT_OS_ARCHITECTURE.md) — Agent = Instructions + Knowledge + Skills + Tools + Memory + Workflows  
- [PRODUCT_CONSTITUTION.md](../PRODUCT_CONSTITUTION.md) — master index (when present)  
- [architecture/marketsynth_subsystem_standard.md](../architecture/marketsynth_subsystem_standard.md) — subsystem lifecycle for new domains  
