---
tags: [gemini, scheduler, cron, sqlite, automation]
date: 2026-04-18
type: note
---

# Шаг 9: Планировщик задач (Persistent Scheduler)

Бот выполняет задачи по расписанию и отправляет результат в Telegram. Расписание хранится в SQLite — работает после перезагрузок.

## Prerequisites

- Шаги 4-6 выполнены (бот работает, SQLite настроен)
- `cron-parser` установлен (должен быть из Шага 3)

## Архитектура

Планировщик — это не системный cron. Это polling-цикл внутри процесса бота:
- Каждые 60 секунд проверяет таблицу `scheduled_tasks` в SQLite
- Если `next_run <= NOW()` и задача активна — запускает gemini с промптом
- Результат отправляет в указанный chat_id через Telegram
- Обновляет `next_run` и `last_run`

Преимущества перед системным cron: задачи управляются через Telegram, сохраняются в базе, работают без доступа к серверу.

## Промпт для Gemini CLI

```text
Add a persistent SQLite-based scheduler to GeminiClaw.

## Database schema (add to store/geminiclaw.db)
```sql
CREATE TABLE IF NOT EXISTS scheduled_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  prompt TEXT NOT NULL,
  cron_expression TEXT NOT NULL,   -- standard 5-field cron: "0 7 * * 1"
  next_run INTEGER NOT NULL,       -- unix timestamp
  last_run INTEGER,
  is_active INTEGER NOT NULL DEFAULT 1,   -- 1 = active, 0 = paused
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  label TEXT                       -- optional human-readable name
);
```

## src/scheduler.ts
Create a Scheduler class with methods:

### constructor(bot: Bot)
- Initialize DB connection
- Create table if not exists
- Store bot reference for sending results

### start(): void
- setInterval every 60 seconds: call tick()
- Log "Scheduler started, polling every 60s"

### tick(): void
- Query: SELECT * FROM scheduled_tasks WHERE is_active = 1 AND next_run <= unixepoch()
- For each due task: run it (async, do not block tick)

### runTask(task): Promise<void>
- Run: gemini -p "TASK_PROMPT"
- Send result to task.chat_id via bot.api.sendMessage
- On error: send error message to chat_id
- Update last_run = unixepoch()
- Compute new next_run using cron-parser:
  const parser = require('cron-parser')
  const interval = parser.parseExpression(task.cron_expression)
  const nextRun = Math.floor(interval.next().getTime() / 1000)
  UPDATE next_run = nextRun WHERE id = task.id

### addTask(chatId, prompt, cronExpression, label?): number
- Parse cronExpression — throw readable error if invalid
- Compute first next_run
- INSERT into scheduled_tasks
- Return new task id

### listTasks(chatId): ScheduledTask[]
- SELECT all tasks for chatId, ORDER BY id

### pauseTask(chatId, id): void
- UPDATE is_active = 0 WHERE id = id AND chat_id = chatId

### resumeTask(chatId, id): void
- UPDATE is_active = 1 AND recompute next_run WHERE id = id AND chat_id = chatId

### deleteTask(chatId, id): void
- DELETE WHERE id = id AND chat_id = chatId

## Bot commands for scheduler (add to src/bot.ts)

### /schedule (with no args)
Show help:
```
Управление задачами по расписанию:
/schedule list — список задач
/schedule add "промпт" "крон" [метка] — добавить задачу
/schedule pause <id> — пауза
/schedule resume <id> — возобновить
/schedule delete <id> — удалить

Примеры:
/schedule add "Сделай краткий дайджест последних событий" "0 9 * * 1" "Понедельник дайджест"
/schedule add "Напомни о weekly review" "0 18 * * 5"
```

### /schedule list
If no tasks: "Нет активных задач. Добавь через /schedule add"
Otherwise, format each task:
```
#ID [ACTIVE/PAUSED] LABEL
Промпт: PROMPT (first 60 chars)
Расписание: CRON_EXPRESSION
Следующий запуск: YYYY-MM-DD HH:MM
Последний запуск: YYYY-MM-DD HH:MM или "не запускался"
```

### /schedule add "промпт" "крон" [метка]
Parse arguments: first quoted string = prompt, second quoted string = cron, third optional = label.
Call scheduler.addTask(chatId, prompt, cron, label).
Reply: "#ID создана. Следующий запуск: YYYY-MM-DD HH:MM"

### /schedule pause <id>
Call scheduler.pauseTask(chatId, parseInt(id)).
Reply: "Задача #ID приостановлена."

### /schedule resume <id>
Call scheduler.resumeTask(chatId, parseInt(id)).
Reply: "Задача #ID возобновлена. Следующий запуск: YYYY-MM-DD HH:MM"

### /schedule delete <id>
Ask for confirmation: "Удалить задачу #ID (LABEL)? Ответь: /schedule confirm_delete <id>"
On confirm_delete: call scheduler.deleteTask, reply "Задача #ID удалена."

## Initialize in src/index.ts
```typescript
import { startBot } from './bot.js'
import { Scheduler } from './scheduler.js'
import { bot } from './bot.js'

const scheduler = new Scheduler(bot)
scheduler.start()

startBot().catch(err => { console.error(err); process.exit(1) })
```

After all files created:
```bash
npm run build
pm2 restart geminiclaw
```
```

## Пример: еженедельный дайджест каждый понедельник

```
/schedule add "Подготовь краткий дайджест: что важного произошло на прошлой неделе в AI и автоматизации. Формат: 5 пунктов, каждый 2-3 предложения." "0 9 * * 1" "Понедельник AI-дайджест"
```

Задача будет запускаться каждый понедельник в 9:00 и присылать дайджест в Telegram.

## Troubleshooting

**Задача не запускается в нужное время**
Проверь что timezone сервера совпадает с ожидаемым: `date`. cron-parser использует системное время. Для изменения timezone: `timedatectl set-timezone Europe/Moscow`

**`cron-parser` бросает ошибку на выражение**
Проверь формат: 5 полей (минуты часы день месяц деньНедели). Пример: `0 9 * * 1` — понедельник в 9:00.

**Бот присылает результат задачи даже когда Telegram неактивен**
Сообщение просто доходит позже, когда откроешь Telegram. Это нормальное поведение.

## После этого шага

- [ ] `/schedule list` работает
- [ ] `/schedule add "тест" "*/5 * * * *" "тест"` создаёт задачу
- [ ] Задача срабатывает через 5 минут и присылает ответ
- [ ] `/schedule pause` и `/schedule resume` работают
- [ ] Задача выживает после `pm2 restart geminiclaw`

Следующий шаг: [[10_COMMANDS]]
