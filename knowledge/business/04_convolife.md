# Команда: /convolife

## Что делает

Показывает сколько контекстного окна использовано в текущей сессии. Выдаёт процент загрузки и сколько токенов осталось. Контекстное окно — это "оперативная память" сессии: когда заканчивается, агент забывает начало разговора и качество ответов падает.

## Когда использовать

- Каждые 30-40 минут при активной работе
- Перед запуском тяжёлой задачи (анализ видео, генерация контента)
- Когда кажется, что агент "тупит" или забывает контекст
- Чтобы решить: compact или newchat

## Правила по результатам

| Загрузка | Что делать |
|----------|-----------|
| 0-40% | Всё хорошо, работай |
| 40-60% | Норма, следи |
| 60-75% | Сделай /compact |
| 75-90% | /compact срочно или /newchat |
| 90%+ | /newchat немедленно |

## Как внедрить в своего агента

### Вариант 1 — Через CLAUDE.md

Добавь в `CLAUDE.md`:

```markdown
### convolife
Триггер: пользователь пишет "convolife", "/convolife" или спрашивает про контекст.

Действия:
1. Найди последний JSONL файл в ~/.claude/projects/ (папка проекта)
2. Извлеки последнее значение input_tokens + cache_read_input_tokens
3. Контекстное окно = 200,000 токенов
4. Выведи: "Context: XX% used — ~XXk tokens remaining"
```

### Вариант 2 — Через Skill (рекомендуемый)

Создай `~/.claude/skills/convolife/SKILL.md`:

```markdown
---
name: convolife
description: Check how much context window is used in the current session. Reports percentage used and tokens remaining. Trigger when user says "convolife", "/convolife", or asks about context window.
---

# Convolife — Context Window Monitor

## Instructions

1. Find the latest JSONL file in ~/.claude/projects/{project-slug}/
2. Extract the last input_tokens + cache_read_input_tokens value
3. Context window = 200,000 tokens. Calculate % used.
4. Report: "Context: XX% used — ~XXk tokens remaining"

```python
import json, os, glob

projects_dir = os.path.expanduser("~/.claude/projects/{your-project-slug}")
files = sorted(glob.glob(f"{projects_dir}/*.jsonl"), key=os.path.getmtime, reverse=True)

if not files:
    print("No session files found")
    exit()

latest = files[0]
last_tokens = 0

with open(latest) as f:
    for line in f:
        try:
            obj = json.loads(line)
            usage = obj.get("usage") or obj.get("message", {}).get("usage", {})
            inp = usage.get("input_tokens", 0)
            cache = usage.get("cache_read_input_tokens", 0)
            total = inp + cache
            if total:
                last_tokens = total
        except:
            pass

context_window = 200000
pct = round(last_tokens / context_window * 100, 1)
remaining = round((context_window - last_tokens) / 1000)
print(f"Context: {pct}% used — ~{remaining}k tokens remaining")
```
```

### Промпт для внедрения (скопируй и отправь агенту)

```
Внедри команду /convolife в мою систему. Вот инструкция:

Когда я пишу "convolife" или "/convolife" — покажи загрузку контекстного окна.

Как считать:
1. Найди последний .jsonl файл сессии в ~/.claude/projects/{папка-проекта}/
2. Возьми последнее значение input_tokens + cache_read_input_tokens
3. Контекстное окно = 200,000 токенов
4. Покажи: "Context: XX% used — ~XXk tokens remaining"

Если >60% — предложи /compact
Если >80% — предложи /newchat

Создай skill файл для этого в ~/.claude/skills/convolife/SKILL.md
```

## Примеры использования

**Пример 1 — всё хорошо:**
```
Пользователь: convolife

Агент: Context: 23% used — ~154k tokens remaining
```

**Пример 2 — пора сжимать:**
```
Пользователь: /convolife

Агент: Context: 67% used — ~66k tokens remaining
⚠️ Рекомендую /compact
```

**Пример 3 — критическая загрузка:**
```
Пользователь: convolife

Агент: Context: 91% used — ~18k tokens remaining
🔴 Рекомендую /newchat — качество ответов может деградировать
```

## Связанные команды

- `/compact` — сжимает контекст, когда convolife показывает 60%+
- `/newchat` — полный сброс, когда контекст забит на 80%+
- `/checkpoint` — сохрани важное перед compact/newchat
