# Шаблон скрипта для автономного агента

Скопируй в `~/claudeclaw/scripts/MY_TASK.sh`, замени все места с пометкой `[ЗАМЕНИ]`, запусти вручную.

```bash
#!/usr/bin/env bash
# ============================================================
# Использование:
#   1. Скопируй в ~/claudeclaw/scripts/MY_TASK.sh
#   2. Замени все [ЗАМЕНИ]
#   3. bash scripts/MY_TASK.sh  ← протестируй вручную
#   4. crontab -e  ← добавь в расписание
# ============================================================

set -euo pipefail

# ---- [ЗАМЕНИ] настройки задачи ----
PROJECT_ROOT="/root/claudeclaw"
TASK_NAME="my-task"                  # имя для лога и lock-файла
AGENT_NAME="my-scheduled-task"       # имя файла из ~/.claude/agents/
TASK_PROMPT="Выполни задачу. Сегодня $(date -u '+%Y-%m-%d'). Отправь результат в Telegram."
TIMEOUT_SEC=180                      # максимум секунд
MAX_TURNS=5                          # максимум шагов агента
# -----------------------------------

LOG_FILE="$PROJECT_ROOT/workspace/tmp/${TASK_NAME}.log"
LOCK_FILE="/tmp/${TASK_NAME}.lock"
ENV_FILE="$PROJECT_ROOT/.env"

# Обязательно для cron — без этого claude не найдётся
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"
export HOME="/root"

# Загружаем токены Telegram
BOT_TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
CHAT_ID=$(grep '^ALLOWED_CHAT_ID=' "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")

notify_telegram() {
  local msg="$1"
  [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ] && \
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
      -d "chat_id=${CHAT_ID}" --data-urlencode "text=${msg}" > /dev/null 2>&1 || true
}

# Защита от параллельного запуска
if [ -f "$LOCK_FILE" ]; then
  echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') -- Already running, exit" >> "$LOG_FILE"
  exit 0
fi
touch "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') -- START: $TASK_NAME" >> "$LOG_FILE"

cd "$PROJECT_ROOT"

# Запуск агента
if timeout "$TIMEOUT_SEC" claude \
    --agent "$AGENT_NAME" \
    --max-turns "$MAX_TURNS" \
    -p "$TASK_PROMPT" \
    >> "$LOG_FILE" 2>&1; then
  echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') -- OK" >> "$LOG_FILE"
else
  EXIT_CODE=$?
  echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') -- FAILED (exit $EXIT_CODE)" >> "$LOG_FILE"
  notify_telegram "⚠ ${TASK_NAME} FAILED (exit ${EXIT_CODE})"
fi

# Ротация логов — оставляем последние 500 строк
[ -f "$LOG_FILE" ] && tail -500 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') -- DONE: $TASK_NAME" >> "$LOG_FILE"
```

---

## Готовые строки для crontab -e

```bash
# Каждый день в 07:00 МСК (04:00 UTC)
0 4 * * * bash /root/claudeclaw/scripts/MY_TASK.sh >> /root/claudeclaw/workspace/tmp/MY_TASK.log 2>&1

# Каждый понедельник в 02:00 UTC
0 2 * * 1 bash /root/claudeclaw/scripts/MY_TASK.sh >> /root/claudeclaw/workspace/tmp/MY_TASK.log 2>&1

# Каждое воскресенье в 21:00 UTC (00:00 МСК)
0 21 * * 0 bash /root/claudeclaw/scripts/MY_TASK.sh >> /root/claudeclaw/workspace/tmp/MY_TASK.log 2>&1

# Каждые 2 часа
0 */2 * * * bash /root/claudeclaw/scripts/MY_TASK.sh >> /root/claudeclaw/workspace/tmp/MY_TASK.log 2>&1

# Каждые 15 минут
*/15 * * * * bash /root/claudeclaw/scripts/MY_TASK.sh >> /root/claudeclaw/workspace/tmp/MY_TASK.log 2>&1
```

> Проверить расписание: https://crontab.guru

---

## Что делает каждый блок

| Блок | Зачем |
|------|-------|
| `export PATH` | Без этого cron не находит `claude` |
| `LOCK_FILE` | Защита от параллельного запуска |
| `trap ... EXIT` | Lock удаляется даже если скрипт упал |
| `timeout` | Агент не сожжёт токены если завис |
| `--max-turns` | Ограничение шагов = ограничение стоимости |
| `notify_telegram` | Всегда знаешь если что-то сломалось |
| ротация логов | Лог не растёт бесконечно |
