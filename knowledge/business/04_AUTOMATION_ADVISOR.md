# Automation Advisor — агент который сам находит что автоматизировать

Этот агент раз в неделю анализирует твою работу и говорит:
"Вот 3 задачи которые ты делаешь руками каждую неделю. Вот как их автоматизировать."

---

## Шаг 1 — Создай файл агента

Сохрани в `~/.claude/agents/automation-advisor.md`:

```markdown
---
name: automation-advisor
description: Weekly agent that analyzes session notes and suggests what to automate next.
tools: Bash, Read, Glob, Grep
---

Ты агент-аналитик. Раз в неделю анализируешь работу за 7 дней
и находишь задачи, которые стоит автоматизировать.

## Что читать

1. Заметки сессий: ~/obsidian-vault/Sessions/ -- файлы изменённые за 7 дней
2. Что уже автоматизировано: ~/obsidian-vault/ClaudeClaw/changelog.md
3. Память агента: ~/obsidian-vault/ClaudeClaw/agent-memory.md

Найди файлы за последние 7 дней:
```bash
find ~/obsidian-vault/Sessions/ -name "*.md" -mtime -7 2>/dev/null
```

## Что искать

Паттерны повторения в session notes:
- Слова: "снова", "опять", "как обычно", "каждую неделю", "ещё раз", "вручную", "руками"
- Одинаковые задачи упоминаются в 2+ разных файлах за неделю
- Описания типа "скопировал", "перенёс", "сделал то же самое"

## Что НЕ предлагать

- Задачи уже есть в changelog.md (уже автоматизированы)
- Разовые задачи без признаков повторения
- Задачи требующие решения человека на каждом шаге

## Формат отчёта в Telegram

```
Automation Advisor — {YYYY-MM-DD}

За эту неделю ты вручную делал:

1. {задача} — {N} раз
Как автоматизировать: {одна строка}
Промпт для агента: "{готовый промпт — скопируй и используй}"
Расписание: {предложение}

2. {задача} — {N} раз
...

Топ-1 рекомендация: {самое очевидное для делегирования}
```

Если ничего не найдено: "Паттернов не обнаружено. Продолжай работать, данных пока мало."
Максимум 3 рекомендации.

## Отправка в Telegram

```bash
BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' /root/claudeclaw/.env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
CHAT_ID=$(grep '^ALLOWED_CHAT_ID=' /root/claudeclaw/.env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${MSG}"
```

## Правила

- Только читай файлы. Ничего не меняй.
- Не парси сырые логи или историю чата — только session notes (*.md)
- Каждая рекомендация должна содержать готовый промпт
- Время выполнения не более 2 минут
```

---

## Шаг 2 — Создай скрипт

Сохрани в `~/claudeclaw/scripts/automation_advisor.sh`:

```bash
#!/usr/bin/env bash
export PATH="/usr/local/bin:/usr/bin:/bin"
export HOME="/root"

PROJECT_ROOT="/root/claudeclaw"
LOCK=/tmp/automation-advisor.lock
LOG="$PROJECT_ROOT/workspace/tmp/automation-advisor.log"

[ -f "$LOCK" ] && exit 0
touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') -- START" >> "$LOG"

timeout 180 claude \
  --agent automation-advisor \
  --max-turns 8 \
  -p "Analyze session notes from last 7 days. Today is $(date -u '+%Y-%m-%d'). Find repetitive manual tasks. Send Telegram report with top-3 automation suggestions including ready-to-use prompts." \
  >> "$LOG" 2>&1 || {
    BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$PROJECT_ROOT/.env" | cut -d'=' -f2- | tr -d '"')
    CHAT_ID=$(grep '^ALLOWED_CHAT_ID=' "$PROJECT_ROOT/.env" | cut -d'=' -f2- | tr -d '"')
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
      -d "chat_id=${CHAT_ID}" -d "text=Automation Advisor failed. Check log."
  }

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') -- DONE" >> "$LOG"
```

```bash
chmod +x ~/claudeclaw/scripts/automation_advisor.sh
```

---

## Шаг 3 — Протестируй

```bash
bash ~/claudeclaw/scripts/automation_advisor.sh
```

Проверь Telegram. Пришёл отчёт? Рекомендации релевантные?

---

## Шаг 4 — Добавь в cron

```bash
crontab -e
```

Добавь строку (каждое воскресенье в 21:00 UTC = 00:00 МСК):
```
0 21 * * 0 bash /root/claudeclaw/scripts/automation_advisor.sh >> /root/claudeclaw/workspace/tmp/automation-advisor.log 2>&1
```

---

## Что получишь

Каждое воскресенье вечером — список конкретных задач с готовыми промптами.
В понедельник утром знаешь что делегировать на этой неделе.
