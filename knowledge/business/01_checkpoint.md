# Команда: /checkpoint

## Что делает

Сохраняет 3-5 ключевых итогов текущей сессии в долговременную память агента (SQLite + Obsidian). После сохранения эти факты автоматически подгружаются в каждую новую сессию.

## Когда использовать

- Завершил важную задачу и хочешь, чтобы агент помнил решения
- Перед переключением на другую тему
- Перед `/newchat` (вызывается автоматически)
- Каждые 1-2 часа при длинной работе

## Как внедрить в своего агента

### Вариант 1 — Через CLAUDE.md (самый простой)

Добавь этот блок в файл `CLAUDE.md` твоего агента:

```markdown
### checkpoint
Триггер: пользователь пишет "checkpoint" или "/checkpoint".

Действия:
1. Составь 3-5 пунктов: что сделано, какие решения приняты, что важно запомнить
2. Сохрани в SQLite:
   - Таблица: memories
   - sector: 'semantic'
   - salience: 5.0
   - topic_key: checkpoint_YYYY_MM_DD
3. Сохрани в Obsidian: ~/obsidian-vault/Sessions/YYYY-MM-DD-checkpoint.md
4. Подтверди: "Checkpoint сохранён."
```

### Вариант 2 — Через Skill (продвинутый)

Создай файл `~/.claude/skills/checkpoint/SKILL.md`:

```markdown
---
name: checkpoint
description: Save a structured summary of the current session to the memories database. Trigger when user says "checkpoint" or "/checkpoint".
---

# Checkpoint — Save Session Summary

## Instructions

1. Compose a 3-5 bullet summary of the most important things done or decided in this session
2. Save to SQLite memories table:
   - sector='semantic', salience=5.0, topic_key=checkpoint_YYYY_MM_DD
3. Save to Obsidian at ~/obsidian-vault/Sessions/YYYY-MM-DD-checkpoint.md
4. Confirm to user: "Checkpoint сохранён."
```

### Промпт для внедрения (скопируй и отправь агенту)

```
Внедри команду /checkpoint в мою систему. Вот инструкция:

Когда я пишу "checkpoint" или "/checkpoint" — сохрани 3-5 ключевых итогов текущей сессии.
Сохраняй в два места:
1. SQLite база (таблица memories, sector='semantic', salience=5.0)
2. Markdown файл в Obsidian (Sessions/YYYY-MM-DD-checkpoint.md)

Формат итогов: короткие пункты, факты и решения, без воды.
После сохранения — подтверди одной строкой.

Создай skill файл для этого в ~/.claude/skills/checkpoint/SKILL.md
```

## Примеры использования

**Пример 1 — после настройки проекта:**
```
Пользователь: checkpoint

Агент: Checkpoint сохранён — SQLite + Obsidian.
• Настроен MCP сервер для Firecrawl
• Добавлена интеграция с Google Calendar через gws CLI
• Исправлен баг с парсингом дат в scheduler
```

**Пример 2 — перед сменой темы:**
```
Пользователь: checkpoint

Агент: Checkpoint сохранён.
• Написан сценарий видео про 7 команд (сохранён в Obsidian)
• Создано 7 раздаточных файлов для зрителей
• Формат раздатки: инструкция + промпт для внедрения + примеры
```

**Пример 3 — в конце рабочего дня:**
```
Пользователь: /checkpoint

Агент: Checkpoint сохранён.
• Проанализировано 12 видео конкурентов
• Собран дайджест трендов за неделю
• Выявлен паттерн: видео с цифрами в заголовке дают +40% CTR
```

## Связанные команды

- `/dream` — консолидирует накопленные checkpoint-ы в обобщённые знания
- `/newchat` — автоматически вызывает checkpoint перед сбросом сессии
- `/convolife` — проверь контекст перед checkpoint, чтобы понять нужен ли /compact
