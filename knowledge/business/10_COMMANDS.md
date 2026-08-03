---
tags: [gemini, commands, management, reference]
date: 2026-04-18
type: note
---

# Шаг 10: Команды управления

Полный справочник команд GeminiClaw. Команды реализованы на уровне `src/bot.ts` — не передаются в Gemini без обработки.

## Список команд

### /newchat
Начать новую сессию.

- Сохраняет краткое summary текущей сессии в `~/obsidian-vault/Sessions/` (если vault доступен) и в memories с scope=session
- Генерирует новый `session_id` в базе
- Сбрасывает compact_count до 0
- Очищает in-memory keyword history для topic shift detection

Ответ бота: "Новая сессия начата. Контекст предыдущей сохранён в памяти."

### /compact
Сжать контекст текущей сессии.

- Запрашивает у Gemini краткое summary последних взаимодействий (5-7 пунктов)
- Сохраняет в memories: scope=session, topic_key=compact_summary (заменяет предыдущее)
- Увеличивает compact_count
- При compact_count >= 3: добавляет предупреждение о деградации контекста

Экономия: до 80% токенов при следующем запросе.

### /checkpoint
Сохранить прогресс в долгосрочную память.

- Запрашивает у Gemini 3-5 ключевых фактов из текущей сессии
- Сохраняет в memories с scope=user, salience=4.0
- Сохраняет в `agent-memory.md` с датой

Ответ бота: краткий список сохранённых фактов.

### /model [pro|flash|auto]
Выбрать модель Gemini.

- `pro` — Gemini 2.0 Pro (умнее, медленнее, расходует больше квоты)
- `flash` — Gemini 2.0 Flash (быстрее, экономнее)
- `auto` — автовыбор (по умолчанию, бот сам решает)
- Без аргумента: показывает текущую модель

Настройка сохраняется в SQLite для данного chat_id.

### /recall `<запрос>`
Поиск в истории и памяти.

- Поиск в SQLite memories для данного chat_id
- Поиск в `agent-memory.md` (grep по строке запроса)
- Поиск в vault: `grep -ril "ЗАПРОС" ~/obsidian-vault/ --include="*.md" | head -5`
- Возвращает топ результаты с источником (DB | agent-memory | vault)

Пример: `/recall YouTube анализ`

### /memory
Показать активные воспоминания.

- Возвращает топ-10 активных записей из memories для данного chat_id
- Сортировка по effective_salience (с учётом decay)
- Формат: `[scope] topic_key: content (salience: X.X)`

### /dream
Консолидация памяти.

- Передаёт `agent-memory.md` в Gemini с задачей: удалить дубликаты, объединить похожие записи, убрать устаревшие (scope=session, expires_at < NOW())
- Сохраняет очищенную версию файла
- Сбрасывает истёкшие записи в SQLite (superseded_at = NOW() для expires_at < NOW())

Рекомендуется запускать раз в неделю, не каждый день.

Ответ бота: "Память консолидирована. Удалено: X записей. Осталось: Y."

### /selfaudit
Проверка здоровья системы.

Проверяет компоненты и возвращает отчёт:

```
GeminiClaw Health Check
-----------------------
Gemini CLI:       OK (v1.x.x)
Telegram bot:     OK (online)
SQLite DB:        OK (memories: N, sessions: M)
agent-memory.md:  OK (N строк) | MISSING
Obsidian vault:   OK | NOT FOUND
Scheduler:        OK (N активных задач) | DISABLED
workspace/inbox:  OK (N файлов)
PM2:              OK (geminiclaw online)
```

Реализуется в `src/bot.ts` прямым чтением файлов и запросами в БД (без вызова Gemini).

### /status
Статистика текущей сессии.

- session_id (первые 8 символов)
- Аптайм бота: `process.uptime()` в формате "Xч Yм"
- compact_count для текущего чата
- Количество активных задач в планировщике
- Активная модель

### /schedule
Управление задачами по расписанию. Подробнее: [[09_SCHEDULER]]

Подкоманды: list, add, pause, resume, delete

## Промпт для реализации команд

```text
Implement all management commands in src/bot.ts for GeminiClaw.

All commands are handled in src/bot.ts before reaching gemini spawn.
Commands are registered via bot.command() handlers.
Keep all command handlers serialized through the per-chat queue.

Required commands (see 10_COMMANDS.md for behavior spec):
- /start, /help, /chatid (already done in step 4)
- /newchat — reset session, save summary
- /compact — summarize context, increment compact_count, warn at >= 3
- /checkpoint — extract and save key facts to memory
- /model [pro|flash|auto] — store model preference in SQLite
- /recall <query> — search memories + agent-memory.md + vault
- /memory — show top-10 active memories
- /dream — consolidate agent-memory.md
- /selfaudit — health check without calling gemini
- /status — session stats without calling gemini

For commands that do NOT need gemini (selfaudit, status, chatid, memory):
  Implement directly in Node.js — read files, query DB, format response.

For commands that DO need gemini (compact, checkpoint, dream):
  Spawn gemini with a specific system prompt describing the task.

Store model preference per chat_id in SQLite:
  TABLE user_prefs (chat_id TEXT PRIMARY KEY, model TEXT DEFAULT 'auto', updated_at INTEGER)

Model values map to gemini CLI flags:
  pro   → gemini --model gemini-2.0-pro-exp
  flash → gemini --model gemini-2.0-flash
  auto  → gemini (no --model flag, uses default)

After implementation:
  npm run build
  pm2 restart geminiclaw
```

## После реализации — тестирование

Проверь каждую команду:

```
/status       — должен вернуть статистику без ошибок
/memory       — показывает записи или "память пуста"
/chatid       — возвращает числовой ID
/selfaudit    — показывает health report
/compact      — возвращает summary сессии
/checkpoint   — сохраняет факты и подтверждает
/recall test  — ищет по слову "test" в памяти
/dream        — консолидирует (запускай только если есть записи)
/model flash  — переключает модель
/model        — показывает текущую модель
```

## После этого шага

- [ ] Все команды из списка работают
- [ ] /selfaudit возвращает полный health report
- [ ] /status не вызывает gemini (отвечает мгновенно)
- [ ] /model переключает модель и сохраняет в базе
- [ ] /recall ищет в памяти и vault

Следующий шаг: [[11_PRODUCTION]]
