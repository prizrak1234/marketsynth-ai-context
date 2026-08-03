# CWF.1a — Intent-Driven Entry & Russian UX

**Phase:** CWF.1a  
**Status:** Implemented (frontend)  
**Date:** 2026-07-23

---

## 1. Problem statement

The product workspace resembled an internal developer admin panel:

- Mixed English/Russian navigation
- Single-purpose entry («Проверить идею» only)
- Empty routes exposing API key / `.env` instructions
- Campaign-centric sidebar labels inconsistent with AI-agency positioning

Marketsynth users arrive with **intent** (content, research, launch), not with knowledge of campaigns, Skills, or MCP.

---

## 2. Approved user intents

Central catalog: `web/src/lib/home/user-intent-catalog.ts`

| ID | Title (RU) | Status |
|----|------------|--------|
| `validate-idea` | Проверить идею | **supported** → BIV on `/workspace` |
| `create-content` | Создать контент | **supported** → `/workspace/assistant` |
| `grow-business` | Развивать бизнес | **partial** → assistant + prefilled prompt |
| `market-research` | Исследовать рынок | **partial** → assistant |
| `prepare-launch` | Подготовить запуск | **partial** → assistant (Launch Pack after verdict) |
| `create-website` | Создать сайт или лендинг | **partial** → assistant |

Content sub-intents (mandatory):

- Telegram-пост → **supported**
- Сценарий для YouTube → **supported**
- Контент-план → **supported**
- Пост для соцсетей / Рекламный текст → **partial**

---

## 3. Supported / partial / planned mapping

| User action | Route | Backend |
|-------------|-------|---------|
| Validate idea | `/workspace` → BIV | `createUserRequest` + `runBusinessIdeaValidation` (unchanged) |
| Free text (idea-like) | `/workspace` → BIV | `routeUserIntent` deterministic |
| Free text (other) | `/workspace/assistant` | `HomeExecutionPanel` + `createUserRequest` |
| Content sub-intents | `/workspace/assistant?task=&scenario=` | Same |
| Launch Pack (post-verdict) | `/workspace` verdict panel | CWF.1a Launch Pack (unchanged) |

**Not supported as fully operational:** external Skills, MCP connectors, auto Telegram publish via MCP.

---

## 4. Start-page information architecture

1. Compact brand block (Marketsynth + agency caption)
2. Commercial promise (`home.offer` + `home.support` + three proof points)
3. Primary task input — «Что вы хотите сделать?»
4. Six action category cards
5. Content sub-panel (on «Создать контент»)
6. Recent projects (if real data)

Visual hierarchy: **task → categories → brand → projects**

---

## 5. Navigation changes

Customer sidebar (`workspace-nav.tsx`):

| RU label | Route |
|----------|-------|
| Главная | `/workspace` |
| Проекты | `/workspace/projects` |
| На проверке | `/workspace/review` |
| AI-ассистент | `/workspace/assistant` |
| Каналы | `/workspace/channels` |
| Материалы | `/workspace/assets` |
| Настройки | `/workspace/settings` |

Removed from customer nav: Knowledge, Task history, Beta QA, Internal Operations.

---

## 6. Empty states

| Section | Test ID | CTA |
|---------|---------|-----|
| Projects | `projects-empty` | «Начать работу» → `/workspace` |
| Review queue | `review-queue-empty` | — |
| Channels | `channels-empty` | Settings link |
| Materials | `assets-empty` | — |

---

## 7. API unavailable state

Component: `customer-service-unavailable.tsx`

Customer copy only — no env var names. Dev diagnostics expandable in `NODE_ENV !== 'production'`.

Internal ops `config-missing.tsx` retains developer variant; product workspace uses cookie auth.

---

## 8. SKILL-R0.1 taxonomy mapping

`futureSkillCandidates` on catalog entries — **metadata only**, not shown to customer, not executed.

See `docs/research/SKILL-R0.1-candidate-audit-summary.md`.

---

## 9. Explicit non-goals (CWF.1a)

- LLM intent router
- Skill Registry / executable external Skills
- MCP installation (Higgsfield, Playwright, Telegram MCP, ads)
- Database / API changes
- CWF.1 BIV / Launch Pack logic changes
- Native Telegram publication path changes

---

## 10. Acceptance criteria

- [x] Default UI Russian
- [x] Intent-driven start page with six cards + free text
- [x] Content → Telegram / YouTube / content plan entry
- [x] Idea validation preserved
- [x] Task text preserved via URL + sessionStorage
- [x] Customer-safe API errors
- [x] Meaningful empty states
- [ ] Owner visual acceptance (browser)

---

## 11. Browser acceptance checklist

**A. Telegram post:** Home → Создать контент → Telegram-пост → assistant shows task  
**B. YouTube:** Home → Создать контент → YouTube → assistant shows task  
**C. Idea validation:** Проверить идею → BIV flow  
**D. API unavailable:** No secret instructions in UI  
**E. Empty pages:** Projects / Review / Materials  

E2E: `web/e2e/cwf-intent-entry.spec.ts`
