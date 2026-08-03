# Beta Runbook — первая волна (5–10 тестеров)

**Статус:** операционный runbook после AI.96–AI.100.  
**Технический аудит:** [phase_ai_100_beta_launch_readiness_audit.md](phase_ai_100_beta_launch_readiness_audit.md).

> **Не открывай 600–800 тестеров сразу.** Первая волна — **5–10 человек**, один сценарий, три метрики. Цель — понять путь и язык, а не собрать лавину «ничего не работает».

---

## 1. Go / No-Go (перед приглашением)

Выполни **локально** в корне репозитория `botfazer`:

```bash
uv run alembic upgrade head
uv run pytest tests/test_phase_ai_100_beta_launch_freeze.py tests/test_phase_ai_95_beta_qa_readiness_freeze.py -q
uv run python scripts/smoke_beta_launch.py
```

| Результат | Действие |
|-----------|----------|
| Все три команды зелёные | Можно приглашать **5–10** тестеров |
| Любой fail | **Stop.** Чини, reset/seed при необходимости, прогоняй снова |
| Smoke падает на alembic | Проверь миграции; для CI можно `--skip-alembic`, для беты — нет |

Дополнительно (staging/prod):

- [ ] `BETA_ACCESS_GATE_ENABLED=true`
- [ ] `BETA_ADMIN_ENDPOINTS_ENABLED=true` (или dev-only admin)
- [ ] `TELEGRAM_PUBLISHING_ENABLED=false` (только dry-run, если не договорились иначе)
- [ ] Smoke + seed на **том же** окружении, куда пойдут тестеры

---

## 2. Подготовка одного тестера (admin)

На **каждого** из 5–10 человек:

1. **Создать пользователя** (или принять существующего) + **API key**.
2. **Approve beta:**
   ```bash
   POST /me/beta-admin/users/{user_id}/approve-beta
   Content-Type: application/json
   Authorization: Bearer <admin-key>

   {"notes": "wave-1 tester #3"}
   ```
3. **Проверить доступ:**
   ```bash
   GET /me/beta-access
   ```
   Ожидание: `status=approved`, `can_use_mvp=true`.
4. **Выдать env для UI** (если internal dashboard):
   ```env
   NEXT_PUBLIC_BOTFAZER_API_KEY=<plain-key>
   NEXT_PUBLIC_BOTFAZER_PROJECT_ID=<project-uuid>
   NEXT_PUBLIC_BOTFAZER_API_BASE_URL=<staging-url>
   ```
5. **Опционально — общий demo-проект:** один раз на окружение:
   ```bash
   uv run python scripts/seed_e2e_demo.py
   ```
   Раздать тестерам `project_id` из вывода скрипта (или пусть создают свой проект и идут по чеклисту).

**Не делать:** массовый invite, общий пароль, ключ в чате без 1:1 канала.

---

## 3. Единый сценарий для тестера (скопировать в сообщение)

**Время:** ~45–90 минут.  
**Цель:** пройти MVP-путь один раз и оставить **один** feedback, если что-то сломалось.

### Шаги (строго по порядку)

| # | Где | Что сделать |
|---|-----|-------------|
| 1 | **Dashboard** | Открыть приложение, убедиться что API key и project id настроены |
| 2 | **Beta guide** | Прочитать карточку «Beta guide» — expected path и limitations |
| 3 | **Demo checklist** | Смотреть «MVP demo flow»; если amber banner — запомнить `failed_step` / code |
| 4 | **Onboarding checklist** | Отметить, что уже зелёное; не выдумывать лишние шаги |
| 5 | **AI Chat** | Одно сообщение orchestrator/copywriter на проекте |
| 6 | **Plan** | Approve marketing plan → start execution run → дождаться copywriter |
| 7 | **Content** | Approve copywriter output → content asset approved |
| 8 | **Media** | Media brief approved → placeholder media asset |
| 9 | **Publishing** | Publication package approved → job **queued** |
| 10 | **Dry-run publish** | Dry-run dispatch (не real Telegram) |
| 11 | **Feedback** | Dashboard → «Report a beta issue» **или** `POST /me/beta-feedback` |

Если застрял **до** шага 10 — всё равно шаг 11: один отчёт с `source` = шаг (onboarding / chat / marketing_pipeline / content / media / publishing).

### Что не тестируем в волне 1

- Billing, оплата, тарифы
- Instagram / LinkedIn
- Real Telegram (если не включили явно)
- «А что если 50 проектов / 100 чатов»

---

## 4. Три метрики (собирать только их)

После каждой сессии тестера — **короткая форма** (Notion / Google Form / таблица). Не превращать в support-тикеты.

### A. Где застряли?

| Поле | Пример |
|------|--------|
| `failed_step` из demo checklist | `content`, `publishing`, … |
| `last_error_code` (если есть) | `gate_blocked`, … |
| Свои слова (1 предложение) | «Не нашёл кнопку approve package» |

**Admin:** дублировать в `GET /me/beta-admin/qa-export` → `with_failed_step_count`, смотреть Settings → Beta QA.

### B. Что непонятно?

| Поле | Пример |
|------|--------|
| Экран / карточка | Beta guide, Demo checklist, Channels |
| Формулировка | «Не понял разницу между package и job» |

**Admin:** тег `severity=medium`, `source=other` или по шагу; кластеризовать перед AI.103 (copy fixes).

### C. На каком шаге захотели бросить?

| Поле | Значение |
|------|----------|
| Номер шага 1–11 | `7` |
| Да/Нет бросил | `да` / `нет` |
| Причина (одна фраза) | «План не approve, непонятно где» |

**Правило приоритета:** если «бросил» + `blocker` в feedback → triage в первый день.

---

## 5. Шаблон строки в таблице волны 1

| Tester # | user_id | approved | finished step | stuck at | unclear | quit step | feedback id | notes |
|----------|---------|----------|---------------|----------|---------|-----------|-------------|-------|
| 1 | uuid | yes | 10 | — | plan vs run | — | uuid | |
| 2 | uuid | yes | 6 | content | — | 6 | uuid | |

---

## 6. Ритм admin (ежедневно, 15–30 мин)

1. `GET /me/beta-admin/qa-export` — failed jobs, demo completion, feedback counts.
2. Settings → **Beta QA** — triage open → resolve дубликаты.
3. Если один и тот же `failed_step` у ≥2 тестеров — **не** чини на лету в prod; занеси в backlog **AI.101–AI.105**.
4. Застрявшему тестеру: reset demo (admin) + re-seed **только** если договорились повторить сценарий:
   ```bash
   POST /projects/{project_id}/demo-flow/reset
   uv run python scripts/seed_e2e_demo.py
   ```

---

## 7. Когда расширять волну

| Сигнал | Действие |
|--------|----------|
| ≥5 из 5–10 прошли шаг 10 (dry-run) | Можно +5–10 следующей волны |
| ≥3 blocker на одном `failed_step` | **Stop** набор, sprint AI.101–105 |
| Много `beta_access_pending` без approve | Процесс invite, не продукт |
| QA export / smoke красные | Stop, не добавлять тестеров |

---

## 8. Следующий технический пакет (после первых ответов)

**AI.101–AI.105 — Beta Feedback Triage Sprint** (кодить **после** данных волны 1):

| Phase | Intent |
|-------|--------|
| AI.101 | Feedback severity dashboard improvements |
| AI.102 | Failed-step analytics |
| AI.103 | UX copy fixes from feedback |
| AI.104 | Demo recovery hardening |
| AI.105 | Beta Sprint 1 freeze |

---

## 9. Быстрые команды

```bash
# Регрессия перед каждым расширением волны
uv run pytest tests/test_phase_ai_100_beta_launch_freeze.py tests/test_phase_ai_95_beta_qa_readiness_freeze.py -q
uv run python scripts/smoke_beta_launch.py

# Feedback (тестер)
POST /me/beta-feedback
{"title":"...","description":"...","source":"publishing","severity":"high","safe_context":{"step":"publishing","error_code":"..."}}
```
