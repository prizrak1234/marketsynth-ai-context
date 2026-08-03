# Команда: /schedule create

## Что делает

В исходной заметке здесь был `/loop`, но в CodexClaw отдельной команды `/loop` сейчас нет. Её роль закрывает `/schedule create`: ты создаёшь повторяющуюся задачу по cron-расписанию, а встроенный scheduler выполняет её сам.

## Когда использовать

- Мониторинг PR или деплоя каждые 5 минут
- Периодическая проверка статуса задачи
- Регулярный сбор данных и дайджестов
- Любая задача, которую нужно повторять по расписанию

## Формат в CodexClaw

```text
/schedule create <cron> <prompt>
```

Примеры:

```text
/schedule create */5 * * * * проверь статус PR #47
/schedule create */2 * * * * проверь что сайт отвечает 200 на https://example.com
/schedule create 0 */1 * * * проверь новые письма от клиентов в Gmail
```

## Как внедрить в своего агента

### Через CLAUDE.md

Добавь в `CLAUDE.md`:

```markdown
### schedule
Триггер: пользователь пишет "/schedule create <cron> <prompt>".

Действия:
1. Разбери cron-выражение и prompt
2. Зарегистрируй задачу во встроенном scheduler
3. Подтверди ID задачи, риск и политику
4. Для управления используй /schedule list, /schedule pause, /schedule resume, /schedule delete
```

### Промпт для внедрения

```text
Приведи повторяющиеся задачи к формату CodexClaw через /schedule.

Когда я пишу "/schedule create <cron> <prompt>":
1. Разбери cron-выражение
2. Создай задачу во встроенном scheduler
3. Верни ID задачи и следующее время запуска

Правила:
1. Для просмотра списка используй /schedule list
2. Для остановки используй /schedule pause <taskId> или /schedule delete <taskId>
3. Для возобновления используй /schedule resume <taskId>
```

## Примеры использования

**Пример 1 — мониторинг PR:**

```text
Пользователь: /schedule create */5 * * * * проверь статус PR #47 в репозитории claudeclaw

Агент: Scheduled task created: task_001
Risk: review
Policy: default
```

**Пример 2 — мониторинг деплоя:**

```text
Пользователь: /schedule create */2 * * * * проверь что сайт отвечает 200 на https://example.com

Агент: Scheduled task created: task_002
Risk: review
Policy: default
```

**Пример 3 — сбор данных:**

```text
Пользователь: /schedule create 0 */1 * * * проверь новые письма от клиентов в Gmail

Агент: Scheduled task created: task_003
Risk: review
Policy: default
```

## Связанные команды

- `/schedule list` — покажет все активные задачи
- `/schedule delete` — удалит задачу по ID
- `/convolife` — длинные фоновые процессы всё равно стоит проверять по контексту
- `/compact` — если долго работаешь с одной темой, может понадобиться сжатие
